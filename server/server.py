#!/opt/BotWave/venv/bin/python3
# this path won't be correct if you didnt use the botwave.dpip.lol/install installer or similar.

# BotWave - Server
# A program by Douxx (douxx.tech | github.com/douxxtech)
# https://github.com/dpipstudio/botwave
# https://botwave.dpip.lol
# A DPIP Studio project. https://dpip.lol
# Licensed under GPL-v3.0 (see LICENSE)

import argparse
import asyncio
from datetime import datetime, timezone
import json
import os
import re
import shlex
import sys
import ssl
import shutil
import tempfile
import time
import threading
from typing import Dict, List, Optional
import uuid

# using this to access to the shared dir files
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from shared.alsa import Alsa
from shared.cat import check
from shared.converter import Converter, SUPPORTED_EXTENSIONS
from shared.custom_cmds import CCMD
from shared.env import Env
from shared.handlers import HandlerExecutor
from shared.http import BWHTTPFileServer
from shared.logger import Log, toggle_input
from shared.morser import text_to_morse
from shared.protocol import ProtocolParser, Commands, PROTOCOL_VERSION
from shared.protomanager import ProtoManager
from shared.queue import Queue
from shared.security import PathValidator, SecurityError
from shared.socket import BWWebSocketServer
from shared.sstv import make_sstv_wav
from shared.tips import TipEngine
from shared.tls import gen_cert, save_cert
from shared.version import check_for_updates, versions_compatible
from shared.ws_cmd import WSCMDH

try:
    import readline
    HAS_READLINE = True
except:
    HAS_READLINE = False

class BotWaveClient:
    def __init__(self, client_id: str, websocket, machine_info: dict, protocol_version: str):
        self.client_id = client_id
        self.websocket = websocket
        self.proto = ProtoManager(send_fn=websocket.send)
        self.machine_info = machine_info
        self.protocol_version = protocol_version
        self.connected_at = datetime.now()
        self.last_seen = datetime.now()
        self.authenticated = True  # alr auth via ws
    
    def get_display_name(self) -> str:
        hostname = self.machine_info.get('hostname', 'unknown')
        return f"{hostname} ({self.client_id})"

class BotWaveServer:
    def __init__(self):
        
        self.clients: Dict[str, BotWaveClient] = {}
        
        # main socket & file transfer
        self.ws_server = None
        self.http_server = None
        self.alsa = Alsa()
        
        # state
        self.running = False
        self.queue = Queue(self)

        # utilities
        self.tips = TipEngine()
        self.handlers_executor = HandlerExecutor(self._execute_command)
        self.custom_commands = CCMD(is_server=True)
        self.last_argv = []

        self.loop = None

    @property
    def host(self):
        return Env.get("HOST", "0.0.0.0")
    
    @property
    def ws_port(self):
        return Env.get_int("PORT")

    @property
    def http_port(self):
        return Env.get_int("FPORT")

    @property
    def passkey(self):
        return Env.get("PASSKEY")

    @property
    def wait_start(self):
        return Env.get_bool("WAIT_START")
    
    @property
    def handlers_dir(self):
        return Env.get("HANDLERS_DIR")
    
    @property
    def upload_dir(self):
        return Env.get("UPLOAD_DIR", "/opt/BotWave/uploads/")
    
    @property
    def skip_checks(self):
        return Env.get_bool("SKIP_CHECKS")
    

    async def start(self):
        try:
            self.tips.start() # sanity check

            # tls certs (for https and wss)
            cert_pem, key_pem = gen_cert()
            cert_path, key_path = save_cert(cert_pem, key_pem)
            
            ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ssl_context.load_cert_chain(cert_path, key_path)
            
            Log.tls("Generated self-signed TLS certificate")
            
            self.ws_server = BWWebSocketServer(
                ssl_context=ssl_context,
                on_message_callback=self._handle_client_message,
                on_connect_callback=self._handle_client_connect,
                on_disconnect_callback=self._handle_client_disconnect
            )
            
            await self.ws_server.start()
            
            self.http_server = BWHTTPFileServer(ssl_context=ssl_context)
            
            await self.http_server.start()
            
            Log.server(f"BotWave Server started")
            Log.version(f"Protocol Version: {PROTOCOL_VERSION}")
            
            if self.passkey:
                Log.auth("Server is using authentication with a passkey")
            
            self.running = True

            if Env.get("WS_CMD_PORT"):
                threading.Thread(target=self._start_websocket_server, daemon=True).start()
            
            if not self.skip_checks:
                self._check_updates()
            
            while self.running:
                await asyncio.sleep(1)
            
        except Exception as e:
            Log.error(f"Error starting server: {e}")
            await self.stop()
            raise

    async def stop(self):
        if not self.running:
            return

        Log.server("Shutting down server...")
        
        await self.kick_client("all", "Server is shutting down")
        
        if self.ws_server:
            await self.ws_server.stop()
            Log.server("Main socket stopped")
        
        if self.http_server:
            await self.http_server.stop()
            Log.server("File transfer (HTTP) server stopped")

        self.tips.stop()
        
        self.running = False
        Log.success("Server shutdown complete")

    def _check_updates(self):
        Log.info("Checking for protocol updates...")

        try:
            latest_version = check_for_updates()

            if latest_version:
                Log.update(f"Update available! Latest version: {latest_version}")
                Log.update("Consider updating to the latest version by running 'bw-update' in your shell.")
            else:
                Log.success("You are using the latest protocol version")
        except Exception as e:
            Log.warning("Unable to check for updates (continuing anyway)")

    async def _handle_client_connect(self, client_id: str, websocket):
        return

    async def _handle_client_disconnect(self, client_id: str):
        if client_id in self.clients:
            client = self.clients[client_id]
            Log.warning(f"Client disconnected: {client.get_display_name()}")
            ctx = self._build_context(client_id)
            del self.clients[client_id]
            self.ondisconnect_handlers(context=ctx)

    async def _handle_client_message(self, client_id: Optional[str], message: str, websocket):
        try:
            parsed = ProtocolParser.parse_command(message)
            command = parsed['command']
            args = parsed['args']
            kwargs = parsed['kwargs']
            
            if client_id is None:
                await self._handle_registration(command, args, kwargs, websocket)
                return
            
            if client_id not in self.clients:
                return

            self.clients[client_id].last_seen = datetime.now()

            if self.clients[client_id].proto.dispatch(parsed):
                return
            
            if command == Commands.PONG:
                return
            
            if command == Commands.OK:
                msg = kwargs.get('message', 'OK')
                Log.success(f"{self.clients[client_id].get_display_name()}: {msg}")
                return
            
            if command == Commands.ERROR:
                msg = kwargs.get('message', 'Error')
                Log.error(f"{self.clients[client_id].get_display_name()}: {msg}")
                return
            
            if command == Commands.END:
                filename = kwargs.get('filename', 'unknown')
                msg = kwargs.get('message')
                if msg:
                    Log.error(f"{self.clients[client_id].get_display_name()}: {msg}")
                else:
                    Log.broadcast(f"{self.clients[client_id].get_display_name()}: Finished broadcasting {filename}")
                self.queue.on_broadcast_ended(client_id)
                return
            
            Log.warning(f"Unexpected command from {client_id}: {command}")
            
        except Exception as e:
            Log.error(f"Error handling message: {e}")


    async def _handle_registration(self, command: str, args: list, kwargs: dict, websocket):
        """        
        sequence:
        1. Client sends: REGISTER hostname=X machine=Y system=Z release=W
        2. Client sends: AUTH <passkey> (if server has passkey)
        3. Client sends: VER <version>
        4. Server sends: REGISTER_OK client_id=X server_version=Y
        
        OR server sends error and closes connection.
        """
        
        if not hasattr(websocket, 'reg_data'):
            websocket.reg_data = {
                'machine_info': None,
                'authenticated': False,
                'protocol_version': None
            }
        
        if command == Commands.REGISTER:
            machine_info = {
                'hostname': kwargs.get('hostname', 'unknown'),
                'machine': kwargs.get('machine', 'unknown'),
                'system': kwargs.get('system', 'unknown'),
                'release': kwargs.get('release', 'unknown')
            }
            
            websocket.reg_data['machine_info'] = machine_info
            
            Log.info(f"Registration attempt from {machine_info['hostname']}")
            
            if not self.passkey:
                websocket.reg_data['authenticated'] = True
            
            return
        
        elif command == Commands.AUTH:
            if not self.passkey:
                websocket.reg_data['authenticated'] = True
                return
            
            if not args:
                Log.auth("AUTH command missing passkey")
                error = ProtocolParser.build_response(
                    Commands.AUTH_FAILED,
                    "Missing passkey"
                )
                await websocket.send(error)
                await websocket.close()
                return
            
            client_passkey = args[0]
            
            if client_passkey != self.passkey:
                Log.auth(f"Authentication failed: Invalid passkey")
                error = ProtocolParser.build_response(
                    Commands.AUTH_FAILED,
                    "Invalid passkey"
                )
                await websocket.send(error)
                await websocket.close()
                return
            
            websocket.reg_data['authenticated'] = True
            Log.auth("Client authenticated")
            return
        
        elif command == Commands.VER:
            if not args:
                Log.error("VER command missing version")
                error = ProtocolParser.build_response(
                    Commands.ERROR,
                    message="Missing protocol version"
                )
                await websocket.send(error)
                await websocket.close()
                return
            
            client_version = args[0]
            
            if not versions_compatible(PROTOCOL_VERSION, client_version):
                Log.error(f"Protocol version mismatch!")
                Log.error(f"  Server version: {PROTOCOL_VERSION}")
                Log.error(f"  Client version: {client_version}")
                
                error = ProtocolParser.build_command(
                    Commands.VERSION_MISMATCH,
                    server_version=PROTOCOL_VERSION,
                    client_version=client_version,
                    message=f"Protocol version mismatch. Please update."
                )
                await websocket.send(error)
                await websocket.close()
                return
            
            websocket.reg_data['protocol_version'] = client_version
            
            if (websocket.reg_data['machine_info'] and 
                websocket.reg_data['authenticated'] and 
                websocket.reg_data['protocol_version']):
                
                await self._complete_registration(websocket)

            else:
                if not websocket.reg_data['authenticated']:
                    Log.auth("Client did not authenticate. Perhaps a missing passkey?")

                    error = ProtocolParser.build_response(
                        Commands.AUTH_FAILED,
                        message="Authentication required"
                    )
                    await websocket.send(error)
                    await websocket.close()
            
            return
        
        else:
            Log.warning(f"Unexpected command during registration: {command}")
            error = ProtocolParser.build_response(
                Commands.ERROR,
                f"Expected REGISTER, AUTH, or VER, got {command}"
            )
            await websocket.send(error)
            await websocket.close()


    async def _complete_registration(self, websocket):
        
        reg_data = websocket.reg_data
        machine_info = reg_data['machine_info']
        protocol_version = reg_data['protocol_version']
        hostname = machine_info['hostname']
        ip = "unknown"

        try:
            ip = websocket.remote_address[0]
        except:
            pass
        
        base_client_id = f"{hostname}_{ip}"
        client_id = base_client_id
        counter = 1
        
        while client_id in self.clients:
            Log.warning(f"Client {client_id} already connected -> reconnecting")
            old_client = self.clients[client_id]
            try:
                await old_client.websocket.close()
            except:
                pass
            del self.clients[client_id]
            
            client_id = base_client_id
            break
        
        client = BotWaveClient(
            client_id=client_id,
            websocket=websocket,
            machine_info=machine_info,
            protocol_version=protocol_version
        )
        
        self.clients[client_id] = client
        
        self.ws_server.register_client(websocket, client_id)
        
        response = ProtocolParser.build_command(
            Commands.REGISTER_OK,
            client_id=client_id,
            server_version=PROTOCOL_VERSION
        )
        
        await websocket.send(response)
        
        Log.success(f"Client registered: {client.get_display_name()}")

        if protocol_version != PROTOCOL_VERSION:
            Log.version(f"  Client protocol version: {protocol_version}. Some features may not work correctly.")
        
        delattr(websocket, 'reg_data')
        self.onconnect_handlers(context=self._build_context(client_id))

    def _start_websocket_server(self):
        self.ws_handler = WSCMDH(
            command_executor=self._execute_command,
            onwsjoin_callback=self.onwsjoin_handlers,
            onwsleave_callback=self.onwsleave_handlers
        )
        self.ws_handler.start()

    def _execute_command(self, command: str, interpolate: bool = True):
        try:
            if "#" in command:
                command = command.split("#", 1)[0]

            command = command.strip()
            env = os.environ.copy() # for the subprocesses

            if interpolate:
                command = re.sub( # replace every {var} with the env value, if exists. if not, empty it
                    r'\{(\w+)\}',
                    lambda m: Env.get(m.group(1), ''),
                    command
                )

            if not command:
                return True
                        
            try:
                cmd = shlex.split(command)

            except ValueError as e:
                Log.error(f"Invalid command syntax: {e}")
                return True
            
            self.last_argv = cmd
            
            command_name = cmd[0].lower()
            
            if self.loop and self.loop.is_running():
                try:
                    try:
                        running_loop = asyncio.get_running_loop()
                    except RuntimeError:
                        running_loop = None

                    if running_loop is self.loop:
                        asyncio.create_task(self._execute_command_async(command_name, cmd, env))
                    else:
                        future = asyncio.run_coroutine_threadsafe(
                            self._execute_command_async(command_name, cmd, env),
                            self.loop
                        )
                        future.result(timeout=300)
                except asyncio.TimeoutError:
                    Log.error("Command timeout")
                except Exception as e:
                    Log.error(f"Command error: {e}")
            else:
                Log.error("Server not running")
            
            return command_name != 'exit'
        except Exception as e:
            Log.error(f"Error executing command: {e}")
            return True


    async def _execute_command_async(self, command_name: str, cmd: list, env: Dict[str, str] = None):
        
        # SERVER CONTROL 
        if command_name == 'exit':
            await self.stop()
            return
        
        # CLIENT MANAGEMENT 
        elif command_name == 'list':
            self.list_clients()
            return
        
        elif command_name == 'kick':
            if len(cmd) < 2:
                Log.error("Usage: kick <targets> [reason]")
                return
            reason = " ".join(cmd[2:]) if len(cmd) > 2 else "Kicked by administrator"
            await self.kick_client(cmd[1], reason)
            return
        
        elif command_name == 'update':
            if len(cmd) < 2:
                Log.error("Usage: update <targets> [latest|<version>]")
                return
            update_args = ' '.join(cmd[2:]) if len(cmd) > 2 else ''
            await self.send_update(cmd[1], update_args)
            return
        
        # FILE MANAGEMENT 
        elif command_name == 'upload':
            if len(cmd) < 3:
                Log.error("Usage: upload <targets> <file|folder>")
                return
            await self.upload_file(cmd[1], cmd[2])
            return
        
        elif command_name == 'dl':
            if len(cmd) < 3:
                Log.error("Usage: dl <targets> <url>")
                return
            await self.download_file(cmd[1], cmd[2])
            return
        
        elif command_name == 'lf':
            if len(cmd) < 2:
                Log.error("Usage: lf <targets>")
                return
            await self.list_files(cmd[1])
            return
        
        elif command_name == 'rm':
            if len(cmd) < 3:
                Log.error("Usage: rm <targets> <filename|all>")
                return
            await self.remove_file(cmd[1], cmd[2])
            return
        
        elif command_name == 'sync':
            if len(cmd) < 3:
                Log.error("Usage: sync <targets|folder/> <source_target|folder/>")
                return
            await self.sync_files(cmd[1], cmd[2])
            return
        
        # BROADCAST CONTROL 
        elif command_name == 'start':
            if len(cmd) < 3:
                Log.error("Usage: start <targets> <file> [freq] [loop] [ps] [rt] [pi]")
                return
                
            frequency = float(cmd[3]) if len(cmd) > 3 else Env.get_int("DEFAULT_FREQ", 90)
            loop = cmd[4].lower() == 'true' if len(cmd) > 4 else False
            ps = cmd[5] if len(cmd) > 5 else Env.get("DEFAULT_PS", "BotWave")
            rt = cmd[6] if len(cmd) > 6 else Env.get("DEFAULT_RT", cmd[2]) # file name
            pi = cmd[7] if len(cmd) > 7 else Env.get("DEFAULT_PI", "FFFF")
            
            await self.start_broadcast(cmd[1], cmd[2], frequency, ps, rt, pi, loop)
            return

        elif command_name == 'live':
            if len(cmd) < 2:
                Log.error("Usage: live <targets> [freq] [ps] [rt] [pi]")
                return
            
            frequency = float(cmd[2]) if len(cmd) > 2 else Env.get_int("DEFAULT_FREQ", 90)
            ps = cmd[3] if len(cmd) > 3 else Env.get("DEFAULT_PS", "BotWave")
            rt = cmd[4] if len(cmd) > 4 else Env.get("DEFAULT_RT", "Broadcasting")
            pi = cmd[5] if len(cmd) > 5 else Env.get("DEFAULT_PI", "FFFF")

            await self.start_live(cmd[1], frequency, ps, rt, pi)
            return

        elif command_name == 'stop':
            if len(cmd) < 2:
                Log.error("Usage: stop <targets>")
                return
            
            self.queue.manual_pause()
            
            await self.stop_broadcast(cmd[1])
            return
        
        elif command_name == 'queue':
            self.queue.parse(' '.join(cmd[1:]))
            return
        
        # OTHER MEDIA FORM
        elif command_name == 'sstv':
            if len(cmd) < 3:
                Log.error("Usage: sstv <targets> <image_path> [mode] [output_wav] [freq] [loop] [ps] [rt] [pi]")
                return
            
            targets = cmd[1]
            img_path = cmd[2]
            mode = cmd[3] if len(cmd) > 3 else None
            output_wav = cmd[4] if len(cmd) > 4 else os.path.join(tempfile.gettempdir(), os.path.splitext(os.path.basename(img_path))[0] + ".wav")
            frequency = float(cmd[5]) if len(cmd) > 5 else Env.get_int("DEFAULT_FREQ", 90)
            loop = cmd[6].lower() == 'true' if len(cmd) > 6 else False
            ps = cmd[7] if len(cmd) > 7 else Env.get("DEFAULT_PS", "BotWave")
            rt = cmd[8] if len(cmd) > 8 else Env.get("DEFAULT_RT", output_wav)
            pi = cmd[9] if len(cmd) > 9 else Env.get("DEFAULT_PI", "FFFF")
            
            if not os.path.exists(img_path):
                Log.error(f"Image file {img_path} not found")
                return
            
            Log.sstv(f"Generating SSTV WAV from {img_path}...")
            success = make_sstv_wav(img_path, output_wav, mode)
            
            if success:
                Log.sstv(f"Uploading {output_wav} to {targets}...")
                await self.upload_file(targets, output_wav)
                await asyncio.sleep(2)  # Wait for upload
                
                Log.sstv(f"Broadcasting {os.path.basename(output_wav)}...")
                await self.start_broadcast(targets, os.path.basename(output_wav), frequency, ps, rt, pi, loop)
            return
        
        # MORSE
        elif command_name == 'morse':
            if len(cmd) < 3:
                Log.error("Usage: morse <targets> <text|file> [wpm] [freq] [loop] [ps] [rt] [pi]")
                return

            targets = cmd[1]
            text_source = cmd[2]

            if os.path.exists(text_source) and os.path.isfile(text_source):
                try:
                    with open(text_source, "r", encoding="utf-8") as f:
                        text = f.read()
                    Log.morse(f"Loaded Morse text from file: {text_source}")
                except Exception as e:
                    Log.error(f"Failed to read text file: {e}")
                    return
            else:
                text = text_source

            wpm = int(cmd[3]) if len(cmd) > 3 else Env.get_int("DEFAULT_MORSE_WPM", 20)
            morse_freq = Env.get_int("MORSE_FREQUENCY", 700)
            frequency = float(cmd[4]) if len(cmd) > 4 else Env.get_int("DEFAULT_FREQ", 90)
            loop = cmd[5].lower() == 'true' if len(cmd) > 5 else False
            ps = cmd[6] if len(cmd) > 6 else Env.get("DEFAULT_PS", "BotWave")
            rt = cmd[7] if len(cmd) > 7 else Env.get("DEFAULT_RT", "Morse")
            pi = cmd[8] if len(cmd) > 8 else Env.get("DEFAULT_PI", "FFFF")

            output_wav = os.path.join(tempfile.gettempdir(), f"morse_{uuid.uuid4().hex[:8]}.wav")

            Log.morse(f"Generating Morse WAV ({wpm} WPM @ {morse_freq}Hz)...")

            success = text_to_morse(text=text, filename=output_wav, wpm=wpm, frequency=morse_freq, sample_rate=Env.get_int("MORSE_SAMPLE_RATE", 48000))

            if not success or not os.path.exists(output_wav):
                Log.error("Failed to generate Morse WAV")
                return

            Log.morse(f"Uploading {output_wav} to {targets}...")
            await self.upload_file(targets, output_wav)
            await asyncio.sleep(2)

            os.remove(output_wav)

            Log.morse("Broadcasting Morse...")
            await self.start_broadcast(targets, os.path.basename(output_wav), frequency=frequency, ps=ps, rt=rt, pi=pi, loop=loop)

            return
        
        # ENVIRONMENT
        elif command_name == 'get':
            if len(cmd) < 2:
                Log.error("Usage: get <keys|*>")
                return
            
            self.print_envkeys(cmd[1:])

            return

        elif command_name == 'set':
            if len(cmd) < 3:
                Log.error("Usage: set <key> <value> [immutable]")
                return
            
            self.set_envkey(cmd[1], cmd[2], cmd[3].lower() == 'true' if len(cmd) > 3 else False)
            
            return


        # OTHER 
        elif command_name == 'handlers':
            if len(cmd) > 1:
                self.handlers_executor.list_handler_commands(cmd[1])
            else:
                self.handlers_executor.list_handlers()
            return
        
        elif command_name == '<':
            if len(cmd) < 2:
                Log.error("Usage: < <shell command>")
                return
            
            shell_command = ' '.join(cmd[1:])
            await self.run_shell_command(shell_command, env)
            return
        
        elif command_name == '|':
            if len(cmd) < 2:
                Log.error("Usage: | <shell command>")
                return
            
            shell_command = ' '.join(cmd[1:])
            await self.run_pipe_command(shell_command, env)
            return
        
        elif command_name == 'help':
            self.display_help()
            return
        
        else:

            if self.custom_commands.exists(command_name):
                self.handlers_executor.execute_handler(
                    os.path.join(self.handlers_dir, f"{command_name}.cmd"),
                    self._build_context(),
                    silent=True
                    )
                
            else:

                Log.error(f"Unknown command: {command_name}")
        

    def _build_context(self, client_id: str = None) -> dict:
        ctx = {}

        try:
            argv_env = {f"BW_ARGV{i}": str(v) for i, v in enumerate(self.last_argv)}

            ctx = {
                **argv_env,
                "BW_SYSTEM_HOSTNAME": os.uname().nodename,
                "BW_SYSTEM_MACHINE": os.uname().machine,
                "BW_SYSTEM_SYSTEM": os.uname().sysname,
                "BW_SYSTEM_PROTO": PROTOCOL_VERSION,
                "BW_UPLOAD_DIR": self.upload_dir,
                "BW_HANDLERS_DIR": self.handlers_dir,
                "BW_WS_PORT": str(self.ws_port) if self.ws_port else "0",
                "BW_PASSKEY_SET": "true" if self.passkey else "false",
                "BW_SERVER_CONNECTED_CLIENTS": ",".join(
                        client.machine_info.get("hostname", "unknown") 
                        for client in self.clients.values()
                    ),
            }
        except:
            ...

        # Client info (only when a specific client is referenced)
        if client_id and client_id in self.clients:
            client = self.clients[client_id]
            info = client.machine_info
            ctx.update({
                "BW_CLIENT_ID": client_id,
                "BW_CLIENT_HOSTNAME": info.get("hostname", "unknown"),
                "BW_CLIENT_MACHINE": info.get("machine", "unknown"),
                "BW_CLIENT_SYSTEM": info.get("system", "unknown"),
                "BW_CLIENT_PROTO": client.protocol_version,
                "BW_CLIENT_CONNECTED_AT": client.connected_at.strftime("%Y-%m-%d %H:%M:%S"),
            })

        return ctx

    def onready_handlers(self, dir_path=None, context=None):
        self.handlers_executor.run_handlers("s_onready", dir_path, context or self._build_context())

    def onstart_handlers(self, dir_path=None, context=None):
        self.handlers_executor.run_handlers("s_onstart", dir_path, context or self._build_context())

    def onstop_handlers(self, dir_path=None, context=None):
        self.handlers_executor.run_handlers("s_onstop", dir_path, context or self._build_context())

    def onconnect_handlers(self, dir_path=None, context=None):
        self.handlers_executor.run_handlers("s_onconnect", dir_path, context or self._build_context())

    def ondisconnect_handlers(self, dir_path=None, context=None):
        self.handlers_executor.run_handlers("s_ondisconnect", dir_path, context or self._build_context())

    def onwsjoin_handlers(self, dir_path=None, context=None):
        self.handlers_executor.run_handlers("s_onwsjoin", dir_path, context or self._build_context())

    def onwsleave_handlers(self, dir_path=None, context=None):
        self.handlers_executor.run_handlers("s_onwsleave", dir_path, context or self._build_context())

    async def run_shell_command(self, command: str, env: Dict[str, str] = None):
        try:
            shell = Env.get("CMD_INTERPRETER")
            if shell:
                command = f"{shell} \"{command}\""
            
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            
            try:
                async def read_stream(stream, is_stderr=False):
                    while True:
                        line = await stream.readline()
                        if not line:
                            break

                        if is_stderr:
                            Log.print(line.decode('utf-8'), style="red", end='')
                        
                        else:
                            Log.print(line.decode('utf-8'), end='')

                await asyncio.wait_for(
                    asyncio.gather(
                        read_stream(process.stdout),
                        read_stream(process.stderr, is_stderr=True)
                    ),
                    timeout=30.0
                )
                
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                Log.error("Command execution timeout")
        
        except Exception as e:
            Log.error(f"Error executing shell command: {e}")

    async def run_pipe_command(self, command: str, env: Dict[str, str] = None):
        try:
            
            shell = Env.get("CMD_INTERPRETER")

            if shell:
                command = f"{shell} \"{command}\""

            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            
            async for line in process.stdout:
                line = line.decode('utf-8').strip()
                if line:
                    # schedule each command as a task instead of awaiting directly to prevent blocking
                    asyncio.create_task(
                        self._execute_command_async(line.split()[0].lower(), shlex.split(line))
                    )

        except Exception as e:
            Log.error(f"Error executing pipe command: {e}")

    def list_clients(self):
        if not self.clients:
            Log.warning("No clients connected")
            return
        
        Log.section("Connected Clients")
        
        for client_id, client in self.clients.items():
            info = client.machine_info
            
            Log.print(f"ID: {client_id}", 'bright_white')
            Log.print(f"  Hostname: {info.get('hostname', 'unknown')}", 'cyan')
            Log.print(f"  Machine: {info.get('machine', 'unknown')}", 'cyan')
            Log.print(f"  System: {info.get('system', 'unknown')}", 'cyan')
            Log.print(f"  Protocol Version: {client.protocol_version}", 'cyan')
            Log.print(f"  Connected: {client.connected_at.strftime('%Y-%m-%d %H:%M:%S')}", 'cyan')
            Log.print(f"  Last seen: {client.last_seen.strftime('%Y-%m-%d %H:%M:%S')}", 'cyan')
            Log.print("")

    async def upload_file(self, client_targets, filepath):
        extra = Env.get("EXTRA_ALLOWED_DIRS", "")
        extra_dirs = [d for d in extra.split(":") if d.strip()]

        ALLOWED_SOURCE_DIRS = [
            tempfile.gettempdir(),
            "/opt/BotWave",
            os.path.expanduser("~"),
            *extra_dirs
        ]

        target_clients = self._parse_client_targets(client_targets)
        if not target_clients:
            Log.warning("No client(s) found matching the query")
            return False

        try:
            filepath = PathValidator.validate_read(filepath, ALLOWED_SOURCE_DIRS)
        except Exception as e:
            Log.error(str(e))
            return False

        if os.path.isdir(filepath):
            return await self._upload_folder_contents(client_targets, filepath)

        if not os.path.exists(filepath):
            Log.error(f"File does not exist: {filepath}")
            return False

        MAX_UPLOAD_SIZE = 500 * 1024 * 1024  # 500 MB
        try:
            filesize = os.path.getsize(filepath)
        except OSError as e:
            Log.error(f"Failed to stat file: {e}")
            return False

        if filesize > MAX_UPLOAD_SIZE:
            Log.error(f"File too large ({filesize} bytes)")
            return False

        try:
            filename = PathValidator.sanitize_filename(os.path.basename(filepath))
        except Exception as e:
            Log.error(f"Invalid filename: {e}")
            return False

        name, ext = os.path.splitext(filename)
        ext = ext.lower().lstrip(".")

        converted_path = None

        # not wav = convert
        if ext != "wav":
            if ext not in SUPPORTED_EXTENSIONS:
                Log.error(f"Unsupported file type: .{ext}")
                return False

            tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            tmp.close()

            try:
                Converter.convert_wav(filepath, tmp.name)
                converted_path = tmp.name
                filepath = converted_path
                filename = PathValidator.sanitize_filename(name + ".wav")
            except Exception as e:
                try:
                    os.unlink(tmp.name)
                except Exception:
                    pass
                Log.error(f"Conversion failed: {e}")
                return False

        try:
            filesize = os.path.getsize(filepath)
        except OSError as e:
            Log.error(f"Failed to get file size: {e}")
            if converted_path:
                try:
                    os.unlink(converted_path)
                except Exception:
                    pass
            return False

        try:
            token = self.http_server.create_download_token(filepath)
        except Exception as e:
            Log.error(f"Failed to create download token: {e}")
            if converted_path:
                try:
                    os.unlink(converted_path)
                except Exception:
                    pass
            return False

        success_count = 0

        for client_id in target_clients:
            if client_id not in self.clients:
                Log.error(f"  {client_id}: Client not found")
                continue

            client = self.clients[client_id]

            await client.proto.fire(
                Commands.DOWNLOAD_TOKEN,
                token=token,
                filename=filename,
                size=filesize
            )
            Log.success(f"  {client.get_display_name()}: Download requested")

            success_count += 1

        Log.info(f"Download tokens sent to {success_count}/{len(target_clients)} clients")
        return success_count > 0
    
    async def _upload_folder_contents(self, client_targets: str, folder_path: str):
        if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
            Log.error(f"Folder {folder_path} not found")
            return False

        files = [
            f for f in os.listdir(folder_path)
            if os.path.isfile(os.path.join(folder_path, f))
        ]

        if not files:
            Log.warning(f"No files found in {folder_path}")
            return False

        Log.file(f"Found {len(files)} file(s) in {folder_path}")
        overall_success = 0

        for idx, filename in enumerate(files, 1):
            full_path = os.path.join(folder_path, filename)
            ext = os.path.splitext(filename)[1].lower().lstrip(".")

            if ext == "wav" or ext in SUPPORTED_EXTENSIONS:
                Log.file(f"[{idx}/{len(files)}] Processing {filename}...")
                if await self.upload_file(client_targets, full_path):
                    overall_success += 1
            else:
                Log.warning(f"Skipping unsupported file: {filename}")

            if idx < len(files):
                await asyncio.sleep(0.5)

        Log.info(f"Folder upload completed: {overall_success}/{len(files)} files")
        return overall_success > 0


    async def start_live(self, client_targets: str, frequency: float = 90.0, ps: str = "BotWave", rt: str = "Broadcasting", pi: str = "FFFF"):
        
        target_clients = self._parse_client_targets(client_targets)
        if not target_clients:
            Log.warning("No client(s) found matching the query")
            return False

        if not self.alsa.is_supported():
            Log.alsa("Live broadcast is not supported on this installation.")
            Log.alsa("Did you setup the ALSA loopback card correctly ?")
            return False
        
        self.queue.manual_pause()
        
        if not self.alsa.start():
            return False

        Log.broadcast(f"Sending stream tokens to {len(target_clients)} client(s)...")
        
        results = {'streamed': [], 'failed': []}
        
        for client_id in target_clients:
            if client_id not in self.clients:
                Log.error(f"  {client_id}: Client not found")
                continue
            
            client = self.clients[client_id]
            
            token = self.http_server.create_stream_token(self.alsa.audio_generator(), self.alsa.rate, self.alsa.channels)

            try:
                response = await client.proto.send(
                    Commands.STREAM_TOKEN,
                    token=token,
                    rate=self.alsa.rate,
                    channels=self.alsa.channels,
                    frequency=frequency,
                    ps=ps,
                    rt=rt,
                    pi=pi
                )

                results["streamed"].append(client_id)
                Log.success(f"{client.get_display_name()}: {response['kwargs'].get('message', 'Success')}")

            except TimeoutError:
                results["failed"].append(client_id)
                Log.error(f"{client.get_display_name()}")

            except RuntimeError as e:
                results["failed"].append(client_id)
                Log.error(f"{client.get_display_name()}: {str(e)}")

        Log.print("")    
        Log.info(f"Success: {len(results['streamed'])}, Failure: {len(results['failed'])}")
        
        card = Env.get("ALSA_CARD", 'BotWave')
        Log.alsa(f"To play live, please set your output sound card (ALSA) to '{card}'.")
        Log.alsa(f"We're expecting {self.alsa.rate}kHz on {self.alsa.channels} channels.")

        return len(results["streamed"]) > 0
    
    async def download_file(self, client_targets: str, url: str):
        target_clients = self._parse_client_targets(client_targets)
        if not target_clients:
            Log.warning("No client(s) found matching the query")
            return False
        
        Log.info(f"Requesting download from {len(target_clients)} client(s)...")
        
        for client_id in target_clients:
            if client_id not in self.clients:
                Log.error(f"  {client_id}: Client not found")
                continue
            
            client = self.clients[client_id]
            filename = url.split('/')[-1]
            
            await client.proto.fire(Commands.DOWNLOAD_URL, url=url, filename=filename)
            
            Log.success(f"  {client.get_display_name()}: Download request sent")

        Log.print("")
        Log.info(f"Download requests sent to {len(target_clients)} client(s)")
        
        return True
    

    async def remove_file(self, client_targets: str, filename: str):
        target_clients = self._parse_client_targets(client_targets)
        if not target_clients:
            Log.warning("No client(s) found matching the query")
            return False
        
        Log.info(f"Removing '{filename}' from {len(target_clients)} client(s)...")
        
        for client_id in target_clients:
            if client_id not in self.clients:
                Log.error(f"  {client_id}: Client not found")
                continue
            
            client = self.clients[client_id]
            
            await client.proto.fire(Commands.REMOVE_FILE, filename=filename)
            
            Log.success(f"  {client.get_display_name()}: Remove request sent")
        
        return True
    
    async def sync_files(self, client_targets: str, source: str):
        # Sync files between clients and/or local folders.
        # 
        # Supports:
        # - sync <clients> <source_client> - Sync from one client to others
        # - sync <clients> <folder/> - Sync from local folder to clients
        # - sync <folder/> <source_client> - Sync from client to local folder
        
        Log.info("This feature is in beta and may be unstable.")

        is_target_folder = client_targets.endswith('/')
        is_source_folder = source.endswith('/')
        
        # Case 1: Sync FROM client TO local folder
        if is_target_folder and not is_source_folder:
            target_dir = client_targets.rstrip('/')
            
            if not os.path.exists(target_dir):
                Log.error(f"Directory {target_dir} does not exist")
                return
            
            source_clients = self._parse_client_targets(source)
            if not source_clients or len(source_clients) != 1:
                Log.error(f"Source '{source}' must resolve to exactly one client")
                return False
            
            source_client_id = source_clients[0]
            
            if source_client_id not in self.clients:
                Log.error(f"Source client {source_client_id} not found")
                return False
            
            source_client = self.clients[source_client_id]
            
            Log.info(f"Syncing from {source_client.get_display_name()} to local folder: {target_dir}")
            
            files = await self._request_file_list(source_client_id)

            if not files:
                Log.warning(f"{source_client.get_display_name()} has no files")
                return True
            
            Log.info(f"Found {len(files)} files to sync")
            
            success_count = 0
            
            for file_info in files:
                filename = file_info.get('name')

                try:
                    filename = PathValidator.sanitize_filename(filename)
                except SecurityError as e:
                    Log.error(f"Invalid filename from client: {e}")
                    continue
                
                try:
                    temp_suffix = uuid.uuid4().hex[:8]
                    temp_filename = f".sync_temp_{source_client_id}_{temp_suffix}_{filename}"
                    
                    try:
                        temp_path = PathValidator.safe_join(target_dir, temp_filename)
                        final_path = PathValidator.safe_join(target_dir, filename)
                    except SecurityError as e:
                        Log.error(f"Path traversal attempt in sync: {e}")
                        continue
                    
                    token = self.http_server.create_upload_token(temp_filename, 0, upload_dir=target_dir)
                    
                    self.clients[source_client_id].proto.execute(
                        Commands.UPLOAD_TOKEN,
                        token=token,
                        filename=filename,
                        size=0
                    )
                    
                    Log.client(f"  [{success_count + 1}/{len(files)}] Downloading {filename}...")

                    if not await self._wait_for_file_complete(temp_path):
                        Log.error(f"  {filename} - file never unlocked")
                        continue
                    
                    if os.path.exists(temp_path):
                        try:
                            if os.path.exists(final_path):
                                os.remove(final_path)
                            os.rename(temp_path, final_path)
                            
                            file_size = os.path.getsize(final_path)
                            Log.file(f"  {filename} saved ({file_size} bytes)")
                            success_count += 1
                        except PermissionError:
                            for retry in range(3):
                                await asyncio.sleep(0.5)
                                try:
                                    if os.path.exists(final_path):
                                        os.remove(final_path)
                                    os.rename(temp_path, final_path)
                                    
                                    file_size = os.path.getsize(final_path)
                                    Log.file(f"  {filename} saved ({file_size} bytes)")
                                    success_count += 1
                                    break
                                except PermissionError:
                                    if retry == 2:
                                        raise
                    else:
                        Log.error(f"  {filename} - timeout")
                
                except Exception as e:
                    Log.error(f"  {filename} - {e}")
                    try:
                        if os.path.exists(temp_path):
                            os.remove(temp_path)
                    except:
                        pass
            
            if success_count > 0:
                Log.info(f"Sync completed: {success_count}/{len(files)} files")
                return True
            else:
                Log.error("Sync failed: no files transferred")
                return False
        
        # Case 2: Sync FROM local folder TO clients
        elif is_source_folder:
            source_dir = source.rstrip('/')
            
            if not os.path.exists(source_dir) or not os.path.isdir(source_dir):
                Log.error(f"Source folder {source_dir} not found")
                return False
            
            target_clients = self._parse_client_targets(client_targets)
            if not target_clients:
                return False
            
            supported_files = [
                f for f in os.listdir(source_dir)
                if os.path.isfile(os.path.join(source_dir, f)) and
                (f.lower().endswith('.wav') or os.path.splitext(f)[1].lower().lstrip(".") in SUPPORTED_EXTENSIONS)
            ]

            if not supported_files:
                Log.warning(f"No supported files found in {source_dir}")
                return False
            
            Log.info(f"Syncing from local folder: {source_dir} ({len(supported_files)} files)")
            Log.info(f"Targets: {', '.join(target_clients)}")
            
            Log.info("Clearing existing files on targets...")
            await self.remove_file(','.join(target_clients), "all")
            await asyncio.sleep(1)
            
            success = await self._upload_folder_contents(','.join(target_clients), source_dir)
            
            Log.info(f"Sync completed: {len(supported_files)} file(s) uploaded")
            
            return success
        
        # Case 3: Sync FROM client TO clients
        else:
            source_clients = self._parse_client_targets(source)
            if not source_clients or len(source_clients) != 1:
                Log.error(f"Source '{source}' must resolve to exactly one client")
                return False
            
            source_client_id = source_clients[0]
            
            if source_client_id not in self.clients:
                Log.error(f"Source client {source_client_id} not found")
                return False
            
            target_clients = self._parse_client_targets(client_targets)
            if not target_clients:
                return False
            
            if source_client_id in target_clients:
                target_clients.remove(source_client_id)
            
            if not target_clients:
                Log.warning("No target clients (source was the only target)")
                return False
            
            source_client = self.clients[source_client_id]
            
            Log.info(f"Syncing from {source_client.get_display_name()} to {len(target_clients)} client(s)")
            
            files = await self._request_file_list(source_client_id)
            
            if not files:
                Log.error("Could not get file list from source client")
                return False
            
            Log.info(f"Found {len(files)} files on source")
            Log.info("Downloading files from source client...")
            
            temp_dir = tempfile.mkdtemp(prefix='botwave_sync_')
            downloaded_files = []
            
            try:
                for file_info in files:
                    filename = file_info.get('name')
                    
                    try:
                        temp_suffix = uuid.uuid4().hex[:8]
                        temp_filename = f".sync_temp_{source_client_id}_{temp_suffix}_{filename}"
                        temp_path = os.path.join(temp_dir, temp_filename)
                        final_temp_path = os.path.join(temp_dir, filename)
                        
                        token = self.http_server.create_upload_token(temp_filename, 0, upload_dir=temp_dir)
                        
                        self.clients[source_client_id].proto.execute(
                            Commands.UPLOAD_TOKEN,
                            token=token,
                            filename=filename,
                            size=0
                        )
                        
                        Log.info(f"  Requesting {filename}...")
                        
                        if not await self._wait_for_file_complete(temp_path):
                            Log.error(f"  {filename} - file never unlocked")
                            continue
                        
                        if os.path.exists(temp_path):
                            await asyncio.sleep(0.2)
                            os.rename(temp_path, final_temp_path)
                            downloaded_files.append(filename)
                            Log.file(f"  + {filename}")
                        else:
                            Log.error(f"  {filename} - timeout")
                    
                    except Exception as e:
                        Log.error(f"  {filename} - {e}")
                
                if not downloaded_files:
                    Log.error("Failed to download any files from source")
                    return False
                
                Log.info(f"Downloaded {len(downloaded_files)} files to temp")
                
                Log.info("Clearing files on target clients...")
                await self.remove_file(','.join(target_clients), "all")
                await asyncio.sleep(1)
                
                Log.info("Uploading files to target clients...")
                success = await self._upload_folder_contents(','.join(target_clients), temp_dir)
                
                Log.info(f"Sync completed: {len(downloaded_files)} file(s) transferred")
                
                return success
                
            finally:
                try:
                    shutil.rmtree(temp_dir)
                    Log.info("Cleaned up temporary files")
                except Exception as e:
                    Log.warning(f"Failed to remove temp directory: {e}")

    async def _wait_for_file_complete(self, path, timeout=120):
        last_size = -1
        stable_cycles = 0
        elapsed = 0

        while elapsed < timeout:
            if os.path.exists(path):
                try:
                    size = os.path.getsize(path)

                    with open(path, "rb"):
                        pass

                    if size == last_size:
                        stable_cycles += 1
                    else:
                        stable_cycles = 0
                        last_size = size

                    if stable_cycles >= 3:
                        return True

                except:
                    pass

            await asyncio.sleep(0.5)
            elapsed += 0.5

        return False

    async def start_broadcast(self, client_targets: str, filename: str, frequency: float = 90.0, ps: str = "BotWave", rt: str = "Broadcasting", pi: str = "FFFF", loop: bool = False, trigger_manual:bool = True):
        target_clients = self._parse_client_targets(client_targets)
        
        if not target_clients:
            Log.warning("No client(s) found matching the query")
            return False
        
        if trigger_manual:
            self.queue.manual_pause()
        
        # calculate start_at timestamp if wait_start is enabled
        if self.wait_start and len(target_clients) > 1:
            start_at = datetime.now(timezone.utc).timestamp() + 20 * (len(target_clients) - 1)
            Log.broadcast(f"Starting broadcast at {datetime.fromtimestamp(start_at)}")
        else:
            start_at = 0
            Log.broadcast(f"Starting broadcast ASAP")

        total_count = len(target_clients)
        
        Log.broadcast(f"Starting broadcast on {total_count} client(s)...")

        results = {'started': [], 'failed': []}
        
        for client_id in target_clients:
            if client_id not in self.clients:
                results['failed'].append((client_id, 'not found'))
                continue

            
            client = self.clients[client_id]
            
            try: 
                response = await client.proto.send(
                    Commands.START,
                    filename=filename,
                    freq=frequency,
                    ps=ps,
                    rt=rt,
                    pi=pi,
                    loop='true' if loop else 'false',
                    start_at=start_at
                )

                Log.success(f"{client.get_display_name()}: {response['kwargs'].get('message', 'Broadcast started')}")
                results['started'].append(client_id)

            except TimeoutError:
                Log.error(f"{client.get_display_name()}: Response timeout")
                results['failed'].append((client_id, 'timeout'))

            except RuntimeError as e:
                err = str(e)

                Log.error(f"{client.get_display_name()}: {err}")
                results['failed'].append((client_id, err))

        Log.print("")        
        Log.info(f"Success: {len(results['started'])}, Failure: {len(results['failed'])}")

        self.onstart_handlers(context={**self._build_context(), "BW_BROADCAST_FILE": filename, "BW_BROADCAST_FREQ": str(frequency)})
        return len(results['started']) > 0

    async def stop_broadcast(self, client_targets: str):

        self.alsa.stop()

        target_clients = self._parse_client_targets(client_targets)
        
        if not target_clients:
            Log.warning("No client(s) found matching the query")
            return False
                
        results = {'stopped': [], 'failed': []}
        
        for client_id in target_clients:
            if client_id not in self.clients:
                results['failed'].append((client_id, 'not found'))
                continue

            
            client = self.clients[client_id]
            
            try: 
                response = await client.proto.send(Commands.STOP)

                Log.success(f"{client.get_display_name()}: {response['kwargs'].get('message', 'Broadcast stopped')}")
                results['stopped'].append(client_id)

            except TimeoutError:
                Log.error(f"{client.get_display_name()}: Response timeout")
                results['failed'].append((client_id, 'timeout'))

            except RuntimeError as e:
                err = str(e)

                Log.error(f"{client.get_display_name()}: {err}")
                results['failed'].append((client_id, err))

        Log.print("")        
        Log.info(f"Success: {len(results['stopped'])}, Failure: {len(results['failed'])}")

        self.onstop_handlers()
        return len(results['stopped']) > 0

    async def kick_client(self, client_targets: str, reason: str = "Kicked by administrator"):
        target_clients = self._parse_client_targets(client_targets)
        if not target_clients:
            Log.warning("No client(s) found matching the query")
            return False
        
        Log.client(f"Kicking {len(target_clients)} client(s)...")
        
        results = {'kicked': [], 'failed': []}

        for client_id in target_clients:
            if client_id not in self.clients:
                Log.error(f"  {client_id}: Client not found")
                results["failed"].append(client_id)
                continue
            
            client = self.clients[client_id]
            
            await client.proto.fire(Commands.KICK, reason=reason)
            
            try:
                await client.websocket.close()
            except:
                pass
            
            del self.clients[client_id]
            
            results["kicked"].append(client_id)
            Log.success(f"  {client.get_display_name()}: Kicked - {reason}")

        
        Log.info(f"Success: {len(results['kicked'])}, Failure: {len(results['failed'])}")
        # self.ondisconnect_handlers() (is alr handled by self.ws_server)
        return True
    
    async def send_update(self, targets: str, specifier: str = ''):
        target_clients = self._parse_client_targets(targets)
        if not target_clients:
            Log.warning("No client(s) found matching the query")
            return False

        # preprocess specifier into bw-update args
        args = ''
        if specifier:
            s = specifier.strip().lower()
            if s == 'latest':
                args = '--latest'
            elif re.match(r'^v?\d+\.\d+\.\d+', s):
                args = f'--to {specifier.strip()}'
            else:
                Log.error(f"Invalid version specifier: '{specifier}'. Use 'latest' or a version like 'v1.0.0-oak'")
                return False

        Log.update(f"Sending update request to {len(target_clients)} client(s)...")

        results = {'updated': [], 'failed': []}

        for client_id in target_clients:
            if client_id not in self.clients:
                Log.error(f"  {client_id}: Client not found")
                continue

            client = self.clients[client_id]

            try:
                response = await client.proto.send(
                    Commands.UPDATE,
                    args=args,
                    expected=(Commands.OK, Commands.ERROR),
                    timeout=300.0
                )
                results['updated'].append(client_id)
                Log.success(f"  {client.get_display_name()}: {response['kwargs'].get('message', 'OK')}")

            except TimeoutError:
                results['failed'].append(client_id)
                Log.error(f"  {client.get_display_name()}: Timed out")

            except RuntimeError as e:
                results['failed'].append(client_id)
                Log.error(f"  {client.get_display_name()}: {e}")

        Log.print("")
        Log.info(f"Success: {len(results['updated'])}, Failure: {len(results['failed'])}")

        return len(results['updated']) > 0

    def _parse_client_targets(self, targets: str) -> List[str]:
        if not targets:
            Log.error("No targets specified")
            return []

        if targets.lower() == 'all':
            return list(self.clients.keys())

        target_list = [t.strip() for t in targets.split(',')]
        valid_targets = []

        for target in target_list:
            if target in self.clients:
                valid_targets.append(target)
            else:
                found = False

                for client_id, client in self.clients.items():
                    if client.machine_info.get('hostname') == target:
                        valid_targets.append(client_id)
                        found = True
                        break

                if not found:
                    Log.error(f"Client '{target}' not found")

        return valid_targets


    async def list_files(self, client_targets: str):
        target_clients = self._parse_client_targets(client_targets)
        if not target_clients:
            Log.warning("No client(s) found matching the query")
            return False
        
        results = {'fetched': [], 'failed': []}

        for client_id in target_clients:
            if client_id not in self.clients:
                continue

            client = self.clients[client_id]

            try:
                response = await client.proto.send(Commands.LIST_FILES, timeout=10.0)
                files = json.loads(response['kwargs'].get('files', '[]'))

                Log.success(f"  {client.get_display_name()}: {len(files)} file(s)")

                for f in files:
                    size = f.get('size', 0)
                    if size < 1024: size_str = f"{size} B"
                    elif size < 1024 * 1024: size_str = f"{size / 1024:.1f} KB"
                    else: size_str = f"{size / (1024 * 1024):.1f} MB"
                    Log.print(f"    {f['name']} ({size_str})", 'white')

                results['fetched'].append(client_id)

            except TimeoutError:
                Log.error(f"  {client_id}: Timeout")
                results['failed'].append(client_id)

            except RuntimeError as e:
                Log.error(f"  {client_id}: {e}")
                results['failed'].append(client_id)

        Log.print("")
        Log.info(f"Success: {len(results['fetched'])}, Failure: {len(results['failed'])}")

        return True
    
    async def _request_file_list(self, client_id: str, timeout: int = 30):
        if client_id not in self.clients:
            Log.error(f"Client {client_id} not found")
            return None
        
        try:
            response = await self.clients[client_id].proto.send(Commands.LIST_FILES, timeout=float(timeout))
            return json.loads(response['kwargs'].get('files', '[]'))
        
        except Exception as e:
            Log.error(f"Error getting file list: {e}")
            return None
        

    def print_envkeys(self, keys: List[str]) -> List[str]:
        if "*" in keys:
            keys = list(os.environ.copy().keys())

        for key in keys:
            key = key.upper()
            value, immutable = Env.get(key, get_immutability=True)

            if not value:
                Log.environ(f"'{key}' doesn't exit in the current environment")
                continue

            Log.print("", style="rgb(224,107,61)", icon="ENV", end="")
            Log.print(f"({key})", style="bright_blue", end=" ")
            Log.print(value, style="orange" if immutable else "white")

    def set_envkey(self, key: str, value: str, immutable: bool = False):
        try:
            Env.set(key, value, immutable)
        except ValueError as e:
            Log.environ(str(e))
            return
        
        self.print_envkeys([key])

    def display_help(self):
        Log.header("BotWave Server - Help")
        Log.section("Available Commands")

        Log.print("list", "bright_green")
        Log.print("  List all connected clients", "white")
        Log.print("  Example:", "white")
        Log.print("    list", "cyan")
        Log.print("")

        Log.print("start <targets> <file> [loop] [freq] [ps] [rt] [pi]", "bright_green")
        Log.print("  Start broadcasting on client(s)", "white")
        Log.print("  Example:", "white")
        Log.print("    start all broadcast.wav 100.5 MyRadio", "cyan")
        Log.print("")

        Log.print("stop <targets>", "bright_green")
        Log.print("  Stop broadcasting on client(s)", "white")
        Log.print("  Example:", "white")
        Log.print("    stop all", "cyan")
        Log.print("")

        Log.print("queue [+|-|*|!|?]", "bright_green")
        Log.print("  Manage broadcast queue", "white")
        Log.print("  Use 'queue ?' for detailed help", "white")
        Log.print("")

        Log.print("live <targets> [freq] [ps] [rt] [pi]", "bright_green")
        Log.print("  Start a live audio broadcast to client(s)", "white")
        Log.print("  Example:", "white")
        Log.print("    live all", "cyan")
        Log.print("")

        Log.print("sstv <image_path> [mode] [output_wav] [frequency] [loop] [ps] [rt] [pi]", "bright_green")
        Log.print("  Convert an image into a SSTV WAV file, and then broadcast it", "white")
        Log.print("  Example:", "white")
        Log.print("    sstv /path/to/mycat.png Robot36 cat.wav 90 false PsPs Cutie FFFF", "cyan")
        Log.print("")

        Log.print("morse <targets> <text|file> [wpm] [freq] [loop] [ps] [rt] [pi]", "bright_green")
        Log.print("  Convert text to Morse code WAV and broadcast it", "white")
        Log.print("  Examples:", "white")
        Log.print("    morse all \"CQ CQ DE BOTWAVE\" 18 90 false BOTWAVE MORSE", "cyan")
        Log.print("    morse pi1 message.txt", "cyan")
        Log.print("")

        Log.print("upload <targets> <file|folder>", "bright_green")
        Log.print("  Upload a WAV file or a folder's files to client(s)", "white")
        Log.print("  Examples:", "white")
        Log.print("    upload all broadcast.wav", "cyan")
        Log.print("    upload pi1,pi2 /home/bw/lib", "cyan")
        Log.print("")

        Log.print("sync <targets|folder/> <source_target|folder/>", "bright_green")
        Log.print("  Synchronize files across clients or to/from local folders", "white")
        Log.print("  Examples:", "white")
        Log.print("    sync all pi1", "cyan")
        Log.print("    sync pi2,pi3 /music/", "cyan")
        Log.print("    sync /backup/ pi1", "cyan")
        Log.print("")

        Log.print("dl <targets> <url>", "bright_green")
        Log.print("  Request client(s) to download a file from a URL", "white")
        Log.print("  Example:", "white")
        Log.print("    dl all http://example.com/file.wav", "cyan")
        Log.print("")

        Log.print("lf <targets>", "bright_green")
        Log.print("  List broadcastable files on client(s)", "white")
        Log.print("  Example:", "white")
        Log.print("    lf all", "cyan")
        Log.print("")

        Log.print("rm <targets> <filename|all>", "bright_green")
        Log.print("  Remove a file from client(s)", "white")
        Log.print("  Example:", "white")
        Log.print("    rm all broadcast.wav", "cyan")
        Log.print("")

        Log.print("kick <targets> [reason]", "bright_green")
        Log.print("  Kick client(s) from the server", "white")
        Log.print("  Example:", "white")
        Log.print("    kick pi1 Maintenance", "cyan")
        Log.print("")

        Log.print("update <targets> [latest|<version>]", "bright_green")
        Log.print("  Request client(s) to update and restart", "white")
        Log.print("  Omit version to update to the latest release", "white")
        Log.print("  Examples:", "white")
        Log.print("    update all", "cyan")
        Log.print("    update pi1 latest", "cyan")
        Log.print("    update all v1.0.0-oak", "cyan")
        Log.print("")

        Log.print("handlers [filename]", "bright_green")
        Log.print("  List all handlers or commands in a specific handler file", "white")
        Log.print("  Example:", "white")
        Log.print("    handlers", "cyan")
        Log.print("")

        Log.print("< <command>", "bright_green")
        Log.print("  Run a shell command on the main OS", "white")
        Log.print("  Example:", "white")
        Log.print("    < df -h", "cyan")
        Log.print("")

        Log.print("| <command>", "bright_green")
        Log.print("  Run a shell command and pipe each output line as a BotWave command", "white")
        Log.print("  Example:", "white")
        Log.print("    | cat commands.txt", "cyan")
        Log.print("")

        Log.print("get <keys|*>", "bright_green")
        Log.print("  Get one or more environment variable(s)", "white")
        Log.print("  Use '*' to list all environment variables", "white")
        Log.print("  Examples:", "white")
        Log.print("    get PORT", "cyan")
        Log.print("    get PORT HOST FPORT", "cyan")
        Log.print("    get *", "cyan")
        Log.print("")

        Log.print("set <key> <value> [immutable]", "bright_green")
        Log.print("  Set an environment variable", "white")
        Log.print("  If immutable is 'true', the value cannot be changed without re-setting it as immutable. Editing those values is not recommended.", "white")
        Log.print("  Examples:", "white")
        Log.print("    set PROMPT_TEXT \"._.\"", "cyan")
        Log.print("    set PASSKEY mykey true", "cyan")
        Log.print("")

        Log.print("exit", "bright_green")
        Log.print("  Exit the application", "white")
        Log.print("  Example:", "white")
        Log.print("    exit", "cyan")
        Log.print("")

        Log.print("help", "bright_green")
        Log.print("  Display this help message", "white")
        Log.print("  Example:", "white")
        Log.print("    help", "cyan")
        Log.print("")

        custom_commands = self.custom_commands.get_all()

        if custom_commands:
            Log.section("Custom Commands")

            for command in custom_commands:
                for line in command["help"]:
                    Log.print(line, style="yellow")

                Log.print("")

        Log.section("Targets")

        Log.print("'all' - All connected clients", "white")
        Log.print("client_id - Specific client by ID", "white")
        Log.print("hostname - Client by hostname", "white")
        Log.print("Comma-separated list - Multiple clients", "white")
        Log.print("Example:", "white")
        Log.print("  pi1,pi2", "cyan")
        Log.print("  all", "cyan")
        Log.print("  kitchen-pi", "cyan")


def main():
    Log.header("BotWave - Server")

    check() # from shared.cat !
    
    parser = argparse.ArgumentParser(prog="bw-server", description='BotWave Server')
    parser.add_argument('--host', default=None, help='Server host')
    parser.add_argument('--port', type=int, default=None, help='Server port')
    parser.add_argument('--fport', type=int, default=None, help='File transfer (HTTP) port')
    parser.add_argument('--pk', help='Passkey for authentication')
    parser.add_argument('--handlers-dir', default=None, help='Directory to retrieve s_ handlers from')
    parser.add_argument('--start-asap', action=argparse.BooleanOptionalAction, default=None, dest='start_asap', help='Start broadcasts immediately (may cause client desync)')
    parser.add_argument('--skip-checks', action=argparse.BooleanOptionalAction, default=None, help='Skip system requirements checks')
    parser.add_argument('--rc', type=int, default=None, help='Remote CLI port for remote management')
    parser.add_argument('--daemon', action=argparse.BooleanOptionalAction, help='Run in non-interactive daemon mode')
    args = parser.parse_args()

    def set_prio(key, cli_value, default, immutable=False):
        if cli_value is not None:
            Env.set(key, str(cli_value), immutable=immutable)

        elif not Env.get(key, False) and default is not None:
            Env.set(key, str(default), immutable=immutable)

    set_prio("HOST", args.host, '0.0.0.0', immutable=True)
    set_prio("PORT", args.port, 9938, immutable=True)
    set_prio("FPORT", args.fport, 9921, immutable=True)
    set_prio("HANDLERS_DIR", args.handlers_dir, '/opt/BotWave/handlers/')
    set_prio("SKIP_CHECKS", args.skip_checks, False)
    set_prio("DAEMON", args.daemon, False, immutable=True)
    set_prio("REMOTE_CMD_PORT", args.rc, None, immutable=True)
    set_prio("PASSKEY", args.pk, None, immutable=True)
    set_prio("HISTORY_PATH", None, "/opt/BotWave/.history")
    set_prio("PROMPT_TEXT", None, "botwave › ")
    set_prio("EXTRA_ALLOWED_DIRS", None, os.getcwd())

    if args.start_asap is not None:
        Env.set("WAIT_START", str(not args.start_asap))
    elif not Env.get("WAIT_START", False):
        Env.set("WAIT_START", str(True))        

    server = BotWaveServer()
    
    if Env.get_bool("DAEMON"):
        if Env.get("REMOTE_CMD_PORT"):
            threading.Thread(target=server._start_websocket_server, daemon=True).start()
            time.sleep(1)

        Log.info("Running in daemon mode. Server will continue to run in the background.")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(server.start())
        except (KeyboardInterrupt, asyncio.CancelledError):
            Log.info("Daemon interrupted, shutting down...")
            loop.run_until_complete(server.stop())
        finally:
            loop.close()

    else:
        
        def run_async_server():
            server.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(server.loop)
            server.loop.run_until_complete(server.start())
        
        server_thread = threading.Thread(target=run_async_server, daemon=True)
        server_thread.start()
        
        time.sleep(2)

        if not server.running:
            style = "bold rgb(200,0,0)"

            Log.print("+------------------------------------------------------------+", style)
            Log.print("|                                                            |", style)
            Log.print("|  Server failed to start.                                   |", style)
            Log.print("|                                                            |", style)
            Log.print("|  If there is a stack trace above, please provide it        |", style)
            Log.print("|  when opening an issue.                                    |", style)
            Log.print("|                                                            |", style)
            Log.print("|  If you do not know what is happening, please open an      |", style)
            Log.print("|  issue on GitHub:                                          |", style)
            Log.print("|                                                            |", style)
            Log.print("|  https://github.com/dpipstudio/botwave/issues/new/         |", style)
            Log.print("|                                                            |", style)
            Log.print("+------------------------------------------------------------+", style)

            sys.exit(1)

        if Env.get("REMOTE_CMD_PORT"):
            server._start_websocket_server()

        if HAS_READLINE:
            readline.parse_and_bind('tab: complete')
            readline.parse_and_bind('set editing-mode emacs')
            readline.set_history_length(1000)
            try:
                readline.read_history_file(Env.get("HISTORY_PATH", "/opt/BotWave/.history"))
            except:
                pass
        
        Log.print("Type 'help' for commands", 'bright_yellow')
        
        try:

            server.onready_handlers()
            
            while server.running:
                try:
                    print()
                    toggle_input(True)
                    cmd_input = input(f'\033[1;32m{Env.get("PROMPT_TEXT", "botwave › ")}\033[0m').strip()
                    toggle_input(False)
                    
                    if not cmd_input:
                        continue
                    
                    if HAS_READLINE:
                        readline.add_history(cmd_input)

                    server._execute_command(cmd_input)
                    
                except KeyboardInterrupt:
                    toggle_input(False)
                    Log.warning("Use 'exit' to exit")

                except EOFError:
                    toggle_input(False)
                    Log.info("Exiting...")
                    server.loop.create_task(server.stop())

                except Exception as e:
                    toggle_input(False)
                    Log.error(f"Error: {e}")

        finally:
            if HAS_READLINE:
                try:
                    readline.write_history_file(Env.get("HISTORY_PATH", "/opt/BotWave/.history"))
                except:
                    pass
            server.running = False

if __name__ == "__main__":
    main()