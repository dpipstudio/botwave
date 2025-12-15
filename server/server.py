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
from shared.handlers import HandlerExecutor
from shared.http import BWHTTPFileServer
from shared.logger import Log
from shared.morser import text_to_morse
from shared.protocol import ProtocolParser, Commands, PROTOCOL_VERSION
from shared.socket import BWWebSocketServer
from shared.sstv import make_sstv_wav
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
        self.machine_info = machine_info
        self.protocol_version = protocol_version
        self.connected_at = datetime.now()
        self.last_seen = datetime.now()
        self.authenticated = True  # alr auth via ws
    
    def get_display_name(self) -> str:
        hostname = self.machine_info.get('hostname', 'unknown')
        return f"{hostname} ({self.client_id})"

class BotWaveServer:
    def __init__(self, host: str = '0.0.0.0', ws_port: int = 9938, http_port: int = 9921, ws_cmd_port: int = None, passkey: str = None, wait_start: bool = True, handlers_dir: str = "/opt/BotWave/handlers", upload_dir: str = "/opt/BotWave/uploads"):
        self.host = host
        self.ws_port = ws_port
        self.ws_cmd_port = ws_cmd_port
        self.http_port = http_port
        self.passkey = passkey
        self.wait_start = wait_start
        self.handlers_dir = handlers_dir
        self.upload_dir = upload_dir
        
        self.clients: Dict[str, BotWaveClient] = {}
        
        # main socket & file transfer
        self.ws_server = None
        self.http_server = None
        
        # state
        self.running = False
        self.pending_responses: Dict[str, asyncio.Future] = {}
        self.file_list_responses: Dict[str, list] = {}
        
        # cmd history for interactive mode
        self.command_history = []
        
        self.handlers_executor = HandlerExecutor(handlers_dir, self._execute_command)
        self.loop = None
        
        os.makedirs(upload_dir, exist_ok=True)

    async def start(self):
        try:
            # tls certs (for https and wss)
            cert_pem, key_pem = gen_cert()
            cert_path, key_path = save_cert(cert_pem, key_pem)
            
            ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ssl_context.load_cert_chain(cert_path, key_path)
            
            Log.tls("Generated self-signed TLS certificate")
            
            self.ws_server = BWWebSocketServer(
                host=self.host,
                port=self.ws_port,
                ssl_context=ssl_context,
                on_message_callback=self._handle_client_message,
                on_connect_callback=self._handle_client_connect,
                on_disconnect_callback=self._handle_client_disconnect
            )
            
            await self.ws_server.start()
            
            self.http_server = BWHTTPFileServer(
                host=self.host,
                port=self.http_port,
                ssl_context=ssl_context,
                upload_dir=self.upload_dir
            )
            
            await self.http_server.start()
            
            Log.server(f"BotWave Server started")
            Log.version(f"Protocol Version: {PROTOCOL_VERSION}")
            
            if self.passkey:
                Log.auth("Server is using authentication with a passkey")
            
            self.running = True
            
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
        
        for future in self.pending_responses.values():
            if not future.done():
                future.cancel()
        
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
            del self.clients[client_id]
            self.ondisconnect_handlers()

    async def _handle_client_message(self, client_id: Optional[str], message: str, websocket):
        try:
            parsed = ProtocolParser.parse_command(message)
            command = parsed['command']
            args = parsed['args']
            kwargs = parsed['kwargs']
            
            if client_id is None:
                await self._handle_registration(command, args, kwargs, websocket)
                return
            
            if client_id in self.clients:
                self.clients[client_id].last_seen = datetime.now()
            
            if command == Commands.PONG:
                return
            
            if command == Commands.OK:
                msg = kwargs.get('message', 'OK')
                files_json = kwargs.get('files')
                
                if files_json:
                    try:
                        files = json.loads(files_json)

                        # store file list for sync operations
                        self.file_list_responses[client_id] = files

                        if f"{client_id}_files" in self.pending_responses:
                            self.pending_responses[f"{client_id}_files"].set_result(files)
                            del self.pending_responses[f"{client_id}_files"]
                            return

                        for file in files:
                            Log.file(f"  {file['name']} ({file['size']} bytes)")

                    except Exception as e:
                        Log.error(f"Error parsing files: {e}")
                        
                        if f"{client_id}_files" in self.pending_responses:
                            self.pending_responses[f"{client_id}_files"].set_exception(e)
                            del self.pending_responses[f"{client_id}_files"]

                Log.success(f"{self.clients[client_id].get_display_name()}: {msg}")
                return
            
            if command == Commands.ERROR:
                msg = kwargs.get('message', 'Error')
                Log.error(f"{self.clients[client_id].get_display_name()}: {msg}")
                
                if f"{client_id}_files" in self.pending_responses:
                    self.pending_responses[f"{client_id}_files"].set_exception(Exception(msg))
                    del self.pending_responses[f"{client_id}_files"]
                
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
                    "Missing protocol version"
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
        self.onconnect_handlers()

    def _start_websocket_server(self):
        self.ws_handler = WSCMDH(
            host=self.host,
            port=self.ws_cmd_port,
            passkey=self.passkey,
            command_executor=self._execute_command,
            is_server=True,
            onwsjoin_callback=self.onwsjoin_handlers,
            onwsleave_callback=self.onwsleave_handlers
        )
        self.ws_handler.start()

    def _execute_command(self, command: str):
        # this is only a bridge to _execute_command_async
        try:
            if "#" in command:
                command = command.split("#", 1)[0]
            
            command = command.strip()
            if not command:
                return True
            
            try:
                cmd = shlex.split(command)
            except ValueError as e:
                Log.error(f"Invalid command syntax: {e}")
                return True
            
            command_name = cmd[0].lower()
            
            if self.loop and self.loop.is_running():
                try:
                    future = asyncio.run_coroutine_threadsafe(
                        self._execute_command_async(command_name, cmd),
                        self.loop
                    )
                    future.result(timeout=300)
                except asyncio.TimeoutError:
                    Log.error("Command timeout")
                except Exception as e:
                    Log.error(f"Command error: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                Log.error("Server not running")
            
            return command_name != 'exit'
            
        except Exception as e:
            Log.error(f"Error executing command: {e}")
            return True


    async def _execute_command_async(self, command_name: str, cmd: list):
        
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
        
        elif command_name == 'restart':
            if len(cmd) < 2:
                Log.error("Usage: restart <targets>")
                return
            await self.restart_client(cmd[1])
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
            
            frequency = float(cmd[3]) if len(cmd) > 3 else 90.0
            loop = cmd[4].lower() == 'true' if len(cmd) > 4 else False
            ps = cmd[5] if len(cmd) > 5 else "BotWave"
            rt = cmd[6] if len(cmd) > 6 else "Broadcasting"
            pi = cmd[7] if len(cmd) > 7 else "FFFF"
            
            await self.start_broadcast(cmd[1], cmd[2], frequency, ps, rt, pi, loop)
            return
        
        elif command_name == 'stop':
            if len(cmd) < 2:
                Log.error("Usage: stop <targets>")
                return
            await self.stop_broadcast(cmd[1])
            return
        
        # OTHER MEDIA FORM
        elif command_name == 'sstv':
            if len(cmd) < 3:
                Log.error("Usage: sstv <targets> <image_path> [mode] [output_wav] [freq] [loop] [ps] [rt] [pi]")
                return
            
            targets = cmd[1]
            img_path = cmd[2]
            mode = cmd[3] if len(cmd) > 3 else None
            output_wav = cmd[4] if len(cmd) > 4 else os.path.splitext(os.path.basename(img_path))[0] + ".wav"
            frequency = float(cmd[5]) if len(cmd) > 5 else 90.0
            loop = cmd[6].lower() == 'true' if len(cmd) > 6 else False
            ps = cmd[7] if len(cmd) > 7 else "RADIOOOO"
            rt = cmd[8] if len(cmd) > 8 else "Broadcasting"
            pi = cmd[9] if len(cmd) > 9 else "FFFF"
            
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

            wpm = int(cmd[3]) if len(cmd) > 3 else 20
            frequency = float(cmd[4]) if len(cmd) > 4 else 90
            loop = cmd[5].lower() == 'true' if len(cmd) > 5 else False
            ps = cmd[6] if len(cmd) > 6 else "BOTWAVE"
            rt = cmd[7] if len(cmd) > 7 else "MORSE"
            pi = cmd[8] if len(cmd) > 8 else "FFFF"

            output_wav = f"morse_{uuid.uuid4().hex[:8]}.wav"

            Log.morse(f"Generating Morse WAV ({wpm} WPM @ {frequency}Hz)...")

            success = text_to_morse(text=text, filename=output_wav, wpm=wpm, frequency=frequency)

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
            await self.run_shell_command(shell_command)
            return
        
        elif command_name == 'help':
            self.display_help()
            return
        
        else:
            Log.error(f"Unknown command: {command_name}")
            return

    def onready_handlers(self, dir_path: str = None):
        self.handlers_executor.run_handlers("s_onready", dir_path)

    def onstart_handlers(self, dir_path: str = None):
        self.handlers_executor.run_handlers("s_onstart", dir_path)

    def onstop_handlers(self, dir_path: str = None):
        self.handlers_executor.run_handlers("s_onstop", dir_path)

    def onconnect_handlers(self, dir_path: str = None):
        self.handlers_executor.run_handlers("s_onconnect", dir_path)

    def ondisconnect_handlers(self, dir_path: str = None):
        self.handlers_executor.run_handlers("s_ondisconnect", dir_path)

    def onwsjoin_handlers(self, dir_path: str = None):
        self.handlers_executor.run_handlers("s_onwsjoin", dir_path)

    def onwsleave_handlers(self, dir_path: str = None):
        self.handlers_executor.run_handlers("s_onwsleave", dir_path)

    async def run_shell_command(self, command: str):
        try:
            #Log.info(f"Executing: {command}")
            
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=30.0
                )
                
                if stdout:
                    Log.print(stdout.decode('utf-8'), end='')
                
                if process.returncode != 0 and stderr:
                    Log.info(f"STDERR ({process.returncode}):")
                    Log.print(stderr.decode('utf-8'), end='')
                    
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                Log.error("Command execution timeout")
        
        except Exception as e:
            Log.error(f"Error executing shell command: {e}")

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

    async def upload_file(self, client_targets: str, file_path: str):
        
        if not os.path.exists(file_path):
            Log.error(f"File {file_path} not found")
            return False
        
        if os.path.isdir(file_path):
            return await self._upload_folder_contents(client_targets, file_path)
        
        target_clients = self._parse_client_targets(client_targets)
        if not target_clients:
            return False
        
        filename = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        
        Log.broadcast(f"Uploading {filename} to {len(target_clients)} client(s)...")
        
        success_count = 0
        
        for client_id in target_clients:
            if client_id not in self.clients:
                Log.error(f"  {client_id}: Client not found")
                continue
            
            client = self.clients[client_id]
            
            token = self.http_server.create_download_token(file_path)
            
            command = ProtocolParser.build_command(
                Commands.DOWNLOAD_TOKEN,
                token=token,
                filename=filename,
                size=file_size
            )
            
            await self.ws_server.send(client_id, command)
            
            Log.file(f"  {client.get_display_name()}: Download token sent")
            
            success_count += 1
        
        Log.broadcast(f"Upload tokens sent to {success_count}/{len(target_clients)} clients")
        return success_count > 0
    
    async def _upload_folder_contents(self, client_targets: str, folder_path: str):
        
        if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
            Log.error(f"Folder {folder_path} not found")
            return False
        
        wav_files = [
            f for f in os.listdir(folder_path)
            if f.lower().endswith('.wav') and os.path.isfile(os.path.join(folder_path, f))
        ]
        
        if not wav_files:
            Log.warning(f"No WAV files found in {folder_path}")
            return False
        
        Log.broadcast(f"Found {len(wav_files)} WAV file(s) in {folder_path}")
        
        overall_success = 0
        
        for idx, filename in enumerate(wav_files, 1):
            full_path = os.path.join(folder_path, filename)
            Log.file(f"[{idx}/{len(wav_files)}] Uploading {filename}...")
            
            if await self.upload_file(client_targets, full_path):
                overall_success += 1
            
            if idx < len(wav_files):
                await asyncio.sleep(0.5)
        
        Log.broadcast(f"Folder upload completed: {overall_success}/{len(wav_files)} files")
        return overall_success > 0
    
    
    async def download_file(self, client_targets: str, url: str):
        target_clients = self._parse_client_targets(client_targets)
        if not target_clients:
            return False
        
        Log.broadcast(f"Requesting download from {len(target_clients)} client(s)...")
        
        # Custom command for URL download
        for client_id in target_clients:
            if client_id not in self.clients:
                Log.error(f"  {client_id}: Client not found")
                continue
            
            client = self.clients[client_id]
            filename = url.split('/')[-1]
            
            command = ProtocolParser.build_command(Commands.DOWNLOAD_URL, url=url, filename=filename)
            await self.ws_server.send(client_id, command)
            
            Log.file(f"  {client.get_display_name()}: Download request sent")
        
        return True
    

    async def remove_file(self, client_targets: str, filename: str):
        target_clients = self._parse_client_targets(client_targets)
        if not target_clients:
            return False
        
        Log.broadcast(f"Removing '{filename}' from {len(target_clients)} client(s)...")
        
        for client_id in target_clients:
            if client_id not in self.clients:
                Log.error(f"  {client_id}: Client not found")
                continue
            
            client = self.clients[client_id]
            
            command = ProtocolParser.build_command(Commands.REMOVE_FILE, filename=filename)
            await self.ws_server.send(client_id, command)
            
            Log.file(f"  {client.get_display_name()}: Remove request sent")
        
        return True
    
    async def sync_files(self, client_targets: str, source: str):
        # Sync files between clients and/or local folders.
        # 
        # Supports:
        # - sync <clients> <source_client> - Sync from one client to others
        # - sync <clients> <folder/> - Sync from local folder to clients
        # - sync <folder/> <source_client> - Sync from client to local folder
        
        Log.warning("This feature is in beta and may be unstable.")

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
            
            Log.broadcast(f"Syncing from {source_client.get_display_name()} to local folder: {target_dir}")
            
            files = await self._request_file_list(source_client_id)
            
            if not files:
                Log.error("Could not get file list from client")
                return False
            
            if not files:
                Log.warning(f"{source_client.get_display_name()} has no files")
                return True
            
            Log.info(f"Found {len(files)} files to sync")
            
            success_count = 0
            
            for file_info in files:
                filename = file_info.get('name')
                
                try:
                    temp_suffix = uuid.uuid4().hex[:8]
                    temp_filename = f".sync_temp_{source_client_id}_{temp_suffix}_{filename}"
                    temp_path = os.path.join(target_dir, temp_filename)
                    final_path = os.path.join(target_dir, filename)
                    
                    # FIX 1: Use size 0 instead of 1GB for upload token
                    token = self.http_server.create_upload_token(temp_filename, 0)
                    
                    old_upload_dir = self.http_server.upload_dir
                    self.http_server.upload_dir = target_dir
                    
                    command = ProtocolParser.build_command(
                        Commands.UPLOAD_TOKEN,
                        token=token,
                        filename=filename,
                        size=0
                    )
                    
                    await self.ws_server.send(source_client_id, command)
                    
                    Log.file(f"  [{success_count + 1}/{len(files)}] Downloading {filename}...")
 
                    if not await self._wait_for_file_complete(temp_path):
                            Log.error(f"  {filename} - file never unlocked")
                            continue
                    
                    self.http_server.upload_dir = old_upload_dir
                    
                    if os.path.exists(temp_path):
                        
                        # FIX 3: More robust file replacement
                        try:
                            if os.path.exists(final_path):
                                os.remove(final_path)
                            os.rename(temp_path, final_path)
                            
                            file_size = os.path.getsize(final_path)
                            Log.success(f"  {filename} ({file_size} bytes)")
                            success_count += 1
                        except PermissionError:
                            # If still locked, try a few more times
                            for retry in range(3):
                                await asyncio.sleep(0.5)
                                try:
                                    if os.path.exists(final_path):
                                        os.remove(final_path)
                                    os.rename(temp_path, final_path)
                                    
                                    file_size = os.path.getsize(final_path)
                                    Log.success(f"  {filename} ({file_size} bytes)")
                                    success_count += 1
                                    break
                                except PermissionError:
                                    if retry == 2:
                                        raise
                    else:
                        Log.error(f"  {filename} - timeout")
                        self.http_server.upload_dir = old_upload_dir
                    
                except Exception as e:
                    Log.error(f"  {filename} - {e}")
                    self.http_server.upload_dir = old_upload_dir
                    # Clean up temp file if it exists
                    try:
                        if os.path.exists(temp_path):
                            os.remove(temp_path)
                    except:
                        pass
            
            if success_count > 0:
                Log.broadcast(f"Sync completed: {success_count}/{len(files)} files")
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
            
            wav_files = [
                f for f in os.listdir(source_dir)
                if f.lower().endswith('.wav') and os.path.isfile(os.path.join(source_dir, f))
            ]
            
            if not wav_files:
                Log.warning(f"No WAV files found in {source_dir}")
                return False
            
            Log.broadcast(f"Syncing from local folder: {source_dir} ({len(wav_files)} files)")
            Log.broadcast(f"Targets: {', '.join(target_clients)}")
            
            # Clear files
            Log.info("Clearing existing files on targets...")
            await self.remove_file(','.join(target_clients), "all")
            await asyncio.sleep(1)
            
            success = await self._upload_folder_contents(','.join(target_clients), source_dir)
            
            if success:
                Log.broadcast("Sync completed successfully!")
            else:
                Log.error("Sync completed with errors")
            
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
            
            Log.broadcast(f"Syncing from {source_client.get_display_name()} to {len(target_clients)} client(s)")
            
            files = await self._request_file_list(source_client_id)
            
            if not files:
                Log.error("Could not get file list from source client")
                return False
            
            if not files:
                Log.warning(f"Source client has no files")
                return True
            
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
                        
                        old_upload_dir = self.http_server.upload_dir
                        self.http_server.upload_dir = temp_dir
                        
                        # FIX 1: Use size 0 instead of 1GB
                        token = self.http_server.create_upload_token(temp_filename, 0)
                        
                        command = ProtocolParser.build_command(
                            Commands.UPLOAD_TOKEN,
                            token=token,
                            filename=filename,
                            size=0
                        )
                        
                        await self.ws_server.send(source_client_id, command)
                        
                        Log.file(f"  Downloading {filename}...")
                        
                        if not await self._wait_for_file_complete(temp_path):
                            Log.error(f"  {filename} - file never unlocked")
                            continue

                        
                        self.http_server.upload_dir = old_upload_dir
                        
                        if os.path.exists(temp_path):
                            # FIX 2: Add delay before rename
                            await asyncio.sleep(0.2)
                            os.rename(temp_path, final_temp_path)
                            downloaded_files.append(filename)
                            Log.success(f"  {filename}")
                        else:
                            Log.error(f"  {filename} - timeout")
                            self.http_server.upload_dir = old_upload_dir
                        
                    except Exception as e:
                        Log.error(f"  {filename} - {e}")
                        self.http_server.upload_dir = old_upload_dir
                
                if not downloaded_files:
                    Log.error("Failed to download any files from source")
                    return False
                
                Log.info(f"Downloaded {len(downloaded_files)} files to temp")
                
                Log.info("Clearing files on target clients...")
                await self.remove_file(','.join(target_clients), "all")
                await asyncio.sleep(1)
                
                Log.info("Uploading files to target clients...")
                success = await self._upload_folder_contents(','.join(target_clients), temp_dir)
                
                if success:
                    Log.broadcast("Sync completed successfully!")
                else:
                    Log.error("Sync completed with errors")
                
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



    def _remove_temp_dir(self, directory: str):
        try:
            shutil.rmtree(directory)
        except Exception as e:
            Log.warning(f"Failed to remove temp directory {directory}: {e}")

    async def start_broadcast(self, client_targets: str, filename: str, frequency: float = 90.0, ps: str = "BotWave", rt: str = "Broadcasting", pi: str = "FFFF", loop: bool = False):
        target_clients = self._parse_client_targets(client_targets)
        
        if not target_clients:
            return False
        
        # calculate start_at timestamp if wait_start is enabled
        if self.wait_start and len(target_clients) > 1:
            start_at = datetime.now(timezone.utc).timestamp() + 20 * (len(target_clients) - 1)
            Log.broadcast(f"Starting broadcast at {datetime.fromtimestamp(start_at)}")
        else:
            start_at = 0
            Log.broadcast(f"Starting broadcast ASAP")
        
        command = ProtocolParser.build_command(
            Commands.START,
            filename=filename,
            freq=frequency,
            ps=ps,
            rt=rt,
            pi=pi,
            loop='true' if loop else 'false',
            start_at=start_at
        )
        
        success_count = 0
        total_count = len(target_clients)
        
        Log.broadcast(f"Starting broadcast on {total_count} client(s)...")
        
        for client_id in target_clients:
            if client_id not in self.clients:
                Log.error(f"  {client_id}: Client not found")
                continue
            
            client = self.clients[client_id]
            
            await self.ws_server.send(client_id, command)
            
            Log.success(f"  {client.get_display_name()}: START command sent")
            success_count += 1
        
        Log.broadcast(f"Broadcast start commands sent: {success_count}/{total_count}")
        self.onstart_handlers()
        return success_count > 0

    async def stop_broadcast(self, client_targets: str):
        target_clients = self._parse_client_targets(client_targets)
        
        if not target_clients:
            return False
        
        command = ProtocolParser.build_command(Commands.STOP)
        
        success_count = 0
        
        for client_id in target_clients:
            if client_id not in self.clients:
                Log.error(f"  {client_id}: Client not found")
                continue
            
            client = self.clients[client_id]
            
            await self.ws_server.send(client_id, command)
            
            Log.success(f"  {client.get_display_name()}: STOP command sent")
            success_count += 1
        
        Log.broadcast(f"Broadcast stop commands sent: {success_count}/{len(target_clients)}")
        self.onstop_handlers()
        return success_count > 0

    async def kick_client(self, client_targets: str, reason: str = "Kicked by administrator"):
        target_clients = self._parse_client_targets(client_targets)
        if not target_clients:
            return False
        
        Log.client(f"Kicking {len(target_clients)} client(s)...")
        
        for client_id in target_clients:
            if client_id not in self.clients:
                Log.error(f"  {client_id}: Client not found")
                continue
            
            client = self.clients[client_id]
            
            command = ProtocolParser.build_command(Commands.KICK, reason=reason)
            await self.ws_server.send(client_id, command)
            
            try:
                await client.websocket.close()
            except:
                pass
            
            del self.clients[client_id]
            
            Log.success(f"  {client.get_display_name()}: Kicked - {reason}")
        
        Log.client(f"Kick completed")
        # self.ondisconnect_handlers() (is alr handeled by self.ws_server)
        return True

    async def restart_client(self, client_targets: str):
        target_clients = self._parse_client_targets(client_targets)
        if not target_clients:
            return False
        
        Log.client(f"Requesting restart from {len(target_clients)} client(s)...")
        
        for client_id in target_clients:
            if client_id not in self.clients:
                Log.error(f"  {client_id}: Client not found")
                continue
            
            client = self.clients[client_id]
            
            command = ProtocolParser.build_command(Commands.RESTART)
            await self.ws_server.send(client_id, command)
            
            Log.client(f"  {client.get_display_name()}: Restart request sent")
        
        Log.client(f"Restart requests sent")
        return True

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
            return False
        
        Log.info(f"Listing files from {len(target_clients)} client(s)")
        
        futures = {}
        for client_id in target_clients:
            if client_id not in self.clients:
                Log.error(f"  {client_id}: Client not found")
                continue
            
            future = asyncio.Future()
            futures[client_id] = future
            self.pending_responses[f"{client_id}_files"] = future
            
            client = self.clients[client_id]
            command = ProtocolParser.build_command(Commands.LIST_FILES)
            await self.ws_server.send(client_id, command)
        
        for client_id, future in futures.items():
            try:
                files = await asyncio.wait_for(future, timeout=10.0)
                client = self.clients[client_id]
                
                Log.success(f"  {client.get_display_name()}: {len(files)} file(s)")
                
                if files:
                    for file_info in files:
                        filename = file_info.get('name', 'unknown')
                        size = file_info.get('size', 0)
                        
                        if size < 1024:
                            size_str = f"{size} B"
                        elif size < 1024 * 1024:
                            size_str = f"{size / 1024:.1f} KB"
                        else:
                            size_str = f"{size / (1024 * 1024):.1f} MB"
                        
                        Log.print(f"    {filename} ({size_str})", 'white')
                else:
                    Log.print("    No files found", 'yellow')
                    
            except asyncio.TimeoutError:
                Log.error(f"  {client_id}: Timeout waiting for response")
            except Exception as e:
                Log.error(f"  {client_id}: Error - {e}")
        
        return True
    
    async def _request_file_list(self, client_id: str, timeout: int = 30) -> Optional[list]:
        
        if client_id not in self.clients:
            Log.error(f"Client {client_id} not found")
            return None
        
        future = asyncio.Future()
        self.pending_responses[f"{client_id}_files"] = future
        
        if client_id in self.file_list_responses:
            del self.file_list_responses[client_id]
        
        command = ProtocolParser.build_command(Commands.LIST_FILES)
        await self.ws_server.send(client_id, command)
        
        Log.file(f"Waiting for file list from {client_id}...")
        
        try:
            files = await asyncio.wait_for(future, timeout=timeout)
            return files
        
        except asyncio.TimeoutError:
            Log.error(f"Timeout waiting for file list from {client_id}")
            if f"{client_id}_files" in self.pending_responses:
                del self.pending_responses[f"{client_id}_files"]
            return None
        
        except Exception as e:
            Log.error(f"Error getting file list: {e}")
            return None
        

    def display_help(self):
        Log.header("BotWave Server - Help")
        Log.section("Available Commands")

        Log.print("list", 'bright_green')
        Log.print("  List all connected clients", 'white')
        Log.print("")

        Log.print("start <targets> <file> [loop] [freq] [ps] [rt] [pi]", 'bright_green')
        Log.print("  Start broadcasting on client(s)", 'white')
        Log.print("  Example: start all broadcast.wav 100.5 MyRadio", 'cyan')
        Log.print("")

        Log.print("stop <targets>", 'bright_green')
        Log.print("  Stop broadcasting on client(s)", 'white')
        Log.print("  Example: stop all", 'cyan')
        Log.print("")

        Log.print("sstv <image_path> [mode] [output_wav] [frequency] [loop] [ps] [rt] [pi]", 'bright_green')
        Log.print("  Convert an image into a SSTV WAV file, and then broadcast it", 'white')
        Log.print("  Example: sstv /path/to/mycat.png Robot36 cat.wav 90 false PsPs Cutie FFFF", 'cyan')
        Log.print("")

        Log.print("morse <targets> <text|file> [wpm] [freq] [loop] [ps] [rt] [pi]", 'bright_green')
        Log.print("  Convert text to Morse code WAV and broadcast it", 'white')
        Log.print("  Example: morse all \"CQ CQ DE BOTWAVE\" 18 90 false BOTWAVE MORSE", 'cyan')
        Log.print("  Example: morse pi1 message.txt", 'cyan')
        Log.print("")

        Log.print("upload <targets> <file|folder>", 'bright_green')
        Log.print("  Upload a WAV file or a folder's files to client(s)", 'white')
        Log.print("  Example: upload all broadcast.wav", 'cyan')
        Log.print("  Example: upload pi1,pi2 /home/bw/lib", 'cyan')
        Log.print("")

        Log.print("sync <targets|folder/> <source_target|folder/>", 'bright_green')
        Log.print("  Synchronize files across clients or to/from local folders", 'white')
        Log.print("  Examples:", 'cyan')
        Log.print("    sync all pi1              - Sync from pi1 to all other clients", 'cyan')
        Log.print("    sync pi2,pi3 /music/      - Sync local folder to clients", 'cyan')
        Log.print("    sync /backup/ pi1         - Sync from pi1 to local folder", 'cyan')
        Log.print("")

        Log.print("dl <targets> <url>", 'bright_green')
        Log.print("  Request client(s) to download a file from a URL", 'white')
        Log.print("  Example: dl all http://example.com/file.wav", 'cyan')
        Log.print("")

        Log.print("lf <targets>", 'bright_green')
        Log.print("  List broadcastable files on client(s)", 'white')
        Log.print("  Example: lf all", 'cyan')
        Log.print("")

        Log.print("rm <targets> <filename|all>", 'bright_green')
        Log.print("  Remove a file from client(s)", 'white')
        Log.print("  Example: rm all broadcast.wav", 'cyan')
        Log.print("")
        
        Log.print("kick <targets> [reason]", 'bright_green')
        Log.print("  Kick client(s) from the server", 'white')
        Log.print("  Example: kick pi1 Maintenance", 'cyan')
        Log.print("")

        Log.print("restart <targets>", 'bright_green')
        Log.print("  Request client(s) to restart", 'white')
        Log.print("  Example: restart all", 'cyan')
        Log.print("")

        Log.print("handlers [filename]", 'bright_green')
        Log.print("  List all handlers or commands in a specific handler file", 'white')
        Log.print("  Example: handlers", 'cyan')
        Log.print("")

        Log.print("< <command>", 'bright_green')
        Log.print("  Run a shell command on the main OS", 'white')
        Log.print("  Example: < df -h", 'cyan')
        Log.print("")

        Log.print("exit", 'bright_green')
        Log.print("  Exit the application", 'white')
        Log.print("")

        Log.print("help", 'bright_green')
        Log.print("  Display this help message", 'white')
        Log.print("")

        Log.section("Targets")

        Log.print("'all' - All connected clients", 'white')
        Log.print("client_id - Specific client by ID", 'white')
        Log.print("hostname - Client by hostname", 'white')
        Log.print("Comma-separated list - Multiple clients", 'white')
        Log.print("Example: 'pi1,pi2' or 'all' or 'kitchen-pi'", 'cyan')

def main():
    Log.header("BotWave - Server")
    
    parser = argparse.ArgumentParser(description='BotWave Server')
    parser.add_argument('--host', default='0.0.0.0', help='Server host')
    parser.add_argument('--port', type=int, default=9938, help='Server port')
    parser.add_argument('--fport', type=int, default=9921, help='File transfer (HTTP) port')
    parser.add_argument('--pk', help='Passkey for authentication')
    parser.add_argument('--handlers-dir', default='/opt/BotWave/handlers', help='Directory to retrieve s_ handlers from')
    parser.add_argument('--start-asap', action='store_false', dest='wait_start', help='Start broadcasts immediately (may cause client desync)')
    parser.add_argument('--ws', type=int, help='WebSocket port for remote shell access')
    parser.add_argument('--daemon', action='store_true', help='Run in non-interactive daemon mode')
    args = parser.parse_args()
    
    server = BotWaveServer(
        host=args.host,
        ws_port=args.port,
        http_port=args.fport,
        ws_cmd_port=args.ws,
        passkey=args.pk,
        wait_start=args.wait_start,
        handlers_dir=args.handlers_dir
    )
    
    if args.daemon:
        if args.ws:
            threading.Thread(target=server._start_websocket_server, daemon=True).start()
            time.sleep(1)
        
        asyncio.run(server.start())

    else:
        
        def run_async_server():
            server.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(server.loop)
            server.loop.run_until_complete(server.start())
        
        server_thread = threading.Thread(target=run_async_server, daemon=True)
        server_thread.start()
        
        # give server time to start
        time.sleep(2)

        if args.ws:
            server._start_websocket_server()

        if HAS_READLINE:
            readline.parse_and_bind('tab: complete')
            readline.parse_and_bind('set editing-mode emacs')

            try:
                readline.read_history_file("/opt/BotWave/.history")
            except FileNotFoundError:
                pass

            readline.set_history_length(1000)
        
        Log.print("Type 'help' for commands", 'bright_yellow')
        
        try:

            server.onready_handlers()

            while server.running:
                try:
                    print()
                    cmd_input = input("\033[1;32mbotwave › \033[0m ").strip()
                    
                    if not cmd_input:
                        continue
                    
                    server.command_history.append(cmd_input)

                    if len(server.command_history) > 1000:
                        server.command_history = server.command_history[-1000:]

                    server._execute_command(cmd_input)
                    
                except KeyboardInterrupt:
                    Log.warning("Use 'exit' to exit")
                except EOFError:
                    break
        finally:
            if HAS_READLINE:
                try:
                    readline.write_history_file("/opt/BotWave/.history")
                except:
                    pass
            server.running = False

if __name__ == "__main__":
    main()