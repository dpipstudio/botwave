#!/opt/BotWave/venv/bin/python3
# this path won't be correct if you didnt use the botwave.dpip.lol/install installer or similar.

# BotWave - Server
# A program by Douxx (douxx.tech | github.com/douxxtech)
# https://github.com/dpipstudio/botwave
# https://botwave.dpip.lol
# A DPIP Studios project. https://dpip.lol
# Licensed under GPL-v3.0 (see LICENSE)

import socket
import threading
import json
import os
import sys
import argparse
import time
import asyncio
import websockets
from datetime import datetime, timezone
from typing import Dict, List, Optional
import subprocess
import tempfile

# using this to access to the shared dir files
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from shared.handlers import HandlerExecutor
from shared.logger import Log
from shared.version import PROTOCOL_VERSION, check_for_updates, versions_compatible
from shared.sstv import make_sstv_wav

class BotWaveClient:
    def __init__(self, conn: socket.socket, addr: tuple, machine_info: dict,
                 protocol_version: str = None, passkey: str = None, handlers_dir: str = "/opt/BotWave/handlers"):
        self.conn = conn
        self.addr = addr
        self.machine_info = machine_info
        self.protocol_version = protocol_version or "unknown"
        self.connected_at = datetime.now()
        self.last_seen = datetime.now()
        self.passkey = passkey
        self.authenticated = False
        self.handlers_dir = handlers_dir
        self.uploading = False

    def send_command(self, command: dict) -> Optional[dict]:
        try:
            message = json.dumps(command) + '\n'
            self.conn.send(message.encode('utf-8'))
            response = self.conn.recv(4096).decode('utf-8').strip()
            self.last_seen = datetime.now()
            return json.loads(response)
        except Exception as e:
            Log.error(f"Error sending command to {self.get_display_name()}: {e}")
            return None

    def get_display_name(self) -> str:
        return f"{self.machine_info.get('hostname', 'unknown')} ({self.addr[0]})"

    def is_alive(self) -> bool:
        if self.uploading:
            return True # skip pings while uploading

        try:
            message = '{"type": "ping"}'
            self.conn.send((message + '\n').encode('utf-8'))
            response = self.conn.recv(1024).decode('utf-8').strip()
            self.last_seen = datetime.now()
            return True
        except:
            return False

class BotWaveServer:
    def __init__(self, host: str = '0.0.0.0', port: int = 9938, passkey: str = None, wait_start: bool = True, ws_port: int = None, daemon_mode: bool = False, handlers_dir: str = "/opt/BotWave/handlers"):
        self.host = host
        self.port = port
        self.passkey = passkey
        self.wait_start = wait_start
        self.clients: Dict[str, BotWaveClient] = {}
        self.server_socket = None
        self.running = False
        self.command_history = []
        self.history_index = 0
        self.ws_port = ws_port
        self.ws_server = None
        self.ws_clients = set()
        self.ws_loop = None
        self.daemon_mode = daemon_mode
        self.handlers_dir = handlers_dir
        self.handlers_executor = HandlerExecutor(handlers_dir, self._execute_command)

    def start(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(10)
            self.running = True

            Log.server(f"BotWave Server started on {self.host}:{self.port}")
            Log.version(f"Protocol Version: {PROTOCOL_VERSION}")

            if self.passkey:
                Log.info("Server is using authentication with a passkey")

            threading.Thread(target=self._check_updates_background, daemon=True).start()
            threading.Thread(target=self._accept_clients, daemon=True).start()

            if self.ws_port:
                threading.Thread(target=self._start_websocket_server, daemon=True).start()

            if self.daemon_mode:
                Log.info("Running in daemon mode. Server will continue to run in the background.")
        except Exception as e:
            Log.error(f"Error starting server: {e}")
            sys.exit(1)

    def _check_updates_background(self):
        time.sleep(2)
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

    def _accept_clients(self):
        while self.running:
            try:
                conn, addr = self.server_socket.accept()
                Log.client(f"New connection from {addr[0]}:{addr[1]}")
                threading.Thread(target=self._handle_client, args=(conn, addr), daemon=True).start()
            except Exception as e:
                if self.running:
                    Log.error(f"Error accepting client: {e}")

    def _handle_client(self, conn: socket.socket, addr: tuple):
        try:
            data = conn.recv(1024).decode('utf-8').strip()
            reg_data = json.loads(data)

            if reg_data.get('type') == 'register':
                machine_info = reg_data.get('machine_info', {})
                client_passkey = reg_data.get('passkey')
                client_protocol_version = reg_data.get('protocol_version', 'unknown')

                if not versions_compatible(PROTOCOL_VERSION, client_protocol_version):
                    Log.error(f"Protocol version mismatch for client {addr[0]}:{addr[1]}")
                    Log.error(f"  Server version: {PROTOCOL_VERSION}")
                    Log.error(f"  Client version: {client_protocol_version}")

                    response = {
                        "type": "version_mismatch",
                        "server_version": PROTOCOL_VERSION,
                        "client_version": client_protocol_version,
                        "message": "Protocol version mismatch. Please update your client or server."
                    }

                    conn.send((json.dumps(response) + '\n').encode('utf-8'))
                    conn.close()
                    return

                if self.passkey and client_passkey != self.passkey:
                    Log.error(f"Authentication failed for client {addr[0]}:{addr[1]} - invalid passkey")

                    response = {"type": "auth_failed", "message": "Invalid passkey"}
                    conn.send((json.dumps(response) + '\n').encode('utf-8'))
                    conn.close()
                    return

                client_id = f"{machine_info.get('hostname', 'unknown')}_{addr[0]}"

                if client_id in self.clients:
                    Log.warning(f"Client {client_id} reconnecting - cleaning up old connection")
                    old_client = self.clients[client_id]
                    try:
                        old_client.conn.close()
                    except:
                        pass
                    
                client = BotWaveClient(conn, addr, machine_info, client_protocol_version, self.passkey)
                client.authenticated = True
                self.clients[client_id] = client

                response = {
                    "type": "register_ok",
                    "client_id": client_id,
                    "server_protocol_version": PROTOCOL_VERSION
                }

                conn.send((json.dumps(response) + '\n').encode('utf-8'))
                Log.success(f"Client registered: {client.get_display_name()}")
                Log.version(f"  Client protocol version: {client_protocol_version}")

                self.onconnect_handlers()
                self._keep_client_alive(client_id)
        except Exception as e:
            Log.error(f"Error handling client {addr[0]}:{addr[1]}: {e}")
            conn.close()

    def  _keep_client_alive(self, client_id: str):

        if client_id not in self.clients:
            return

        my_client = self.clients.get(client_id)

        while self.running and client_id in self.clients:
            try:
                current_client = self.clients[client_id]
                
                # if the client object changed, this thread is obsolete
                if current_client is not my_client:
                    break

                client = self.clients[client_id]

                if not client.is_alive():
                    Log.warning(f"Client {client.get_display_name()} disconnected")
                    del self.clients[client_id]
                    self.ondisconnect_handlers()
                    break

                time.sleep(30)
            except Exception as e:
                Log.error(f"Error maintaining connection with {client_id}: {e}")

                if client_id in self.clients:
                    del self.clients[client_id]
                    self.ondisconnect_handlers()

                break

    def _start_websocket_server(self):
        async def handler(websocket):
            self.ws_clients.add(websocket)
            Log.ws_clients = self.ws_clients

            try:
                auth_message = await asyncio.wait_for(websocket.recv(), timeout=5)

                try:
                    auth_data = json.loads(auth_message)
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({"type": "error", "message": "Invalid JSON"}))
                    await websocket.close()
                    return

                if auth_data.get("type") != "auth" or (self.passkey and auth_data.get("passkey") != self.passkey):
                    await websocket.send(json.dumps({"type": "auth_failed", "message": "Invalid passkey"}))
                    await websocket.close()
                    return

                await websocket.send(json.dumps({"type": "auth_ok", "message": "Authenticated"}))
                self.onwsjoin_handlers()

                async for message in websocket:
                    Log.client(f"WebSocket CMD: {message}")

                    def inject_cmd():
                        self.command_history.append(message)
                        self.history_index = len(self.command_history)
                        cmd = message.strip().split()

                        if not cmd:
                            return

                        command = cmd[0].lower()

                        if command == 'list':
                            self.list_clients()

                        elif command == 'help':
                            self.display_help()

                        elif command == 'upload':
                            if len(cmd) < 3:
                                Log.error("Usage: upload <targets> <file>")
                                Log.info("Targets: 'all', client_id, hostname, or comma-separated list")
                                return
                            
                            self.upload_file(cmd[1], cmd[2])

                        elif command == 'start':
                            if len(cmd) < 3:
                                Log.error("Usage: start <targets> <file> [freq] [loop] [ps] [rt] [pi]")
                                Log.info("Targets: 'all', client_id, hostname, or comma-separated list")
                                return
                            
                            frequency = float(cmd[3]) if len(cmd) > 3 else 90.0
                            loop = cmd[4].lower() == 'true' if len(cmd) > 4 else False
                            ps = cmd[5] if len(cmd) > 5 else "BotWave"
                            rt = cmd[6] if len(cmd) > 6 else "Broadcasting"
                            pi = cmd[7] if len(cmd) > 7 else "FFFF"

                            self.start_broadcast(cmd[1], cmd[2], frequency, ps, rt, pi, loop)

                        elif command == 'stop':
                            if len(cmd) < 2:
                                Log.error("Usage: stop <targets>")
                                Log.info("Targets: 'all', client_id, hostname, or comma-separated list")
                                return
                            
                            self.stop_broadcast(cmd[1])

                        elif command == 'kick':
                            if len(cmd) < 2:
                                Log.error("Usage: kick <targets> [reason]")
                                Log.info("Targets: 'all', client_id, hostname, or comma-separated list")
                                return
                            
                            reason = " ".join(cmd[2:]) if len(cmd) > 2 else "Kicked by administrator"
                            self.kick_client(cmd[1], reason)

                        elif command == 'restart':
                            if len(cmd) < 2:
                                Log.error("Usage: restart <targets>")
                                Log.info("Targets: 'all', client_id, hostname, or comma-separated list")
                                return
                            
                            self.restart_client(cmd[1])

                        elif command == 'handlers':
                            if len(cmd) > 1:
                                filename = cmd[1]
                                self.handlers_executor.list_handler_commands(filename)
                            else:
                                self.handlers_executor.list_handlers()

                        elif command == 'lf':
                            if len(cmd) < 2:
                                Log.error("Usage: lf <targets>")
                                Log.info("Targets: 'all', client_id, hostname, or comma-separated list")
                                return
                            
                            self.list_files(cmd[1])

                        elif command == '<':
                            Log.warning("Hmmm, you can't do that. ;)")

                        elif command == 'dl':
                            if len(cmd) < 3:
                                Log.error("Usage: dl <targets> <url>")
                                Log.info("Targets: 'all', client_id, hostname, or comma-separated list")
                                return
                            
                            self.download_file(cmd[1], cmd[2])

                        elif command == 'rm':
                            if len(cmd) < 3:
                                Log.error("Usage: rm <targets> <filename|all>")
                                Log.info("Targets: 'all', client_id, hostname, or comma-separated list")
                                return
                            
                            self.remove_file(cmd[1], cmd[2])

                        elif command == 'sync':
                            if len(cmd) < 3:
                                Log.error("Usage: sync <targets|folder/path/> <source_target|folder/path/>")
                                Log.info("Targets: 'all', client_id, hostname, comma-separated list, or local folder ending with /")
                                Log.info("Source: client_id, hostname, or local folder path ending with /")
                                return

                            self.sync_files(cmd[1], cmd[2])

                        elif command == 'exit':
                            Log.warning("Hmmm, you can't do that. ;)")

                        elif command == '#':
                            # ignore comments
                            pass

                        else:
                            Log.error(f"Unknown WebSocket command: {command}")
                            Log.info("Type 'help' for a list of available commands")

                    asyncio.get_event_loop().call_soon_threadsafe(inject_cmd)
            except asyncio.TimeoutError:
                await websocket.send(json.dumps({"type": "error", "message": "Authentication timeout"}))
                await websocket.close()
                self.onwsleave_handlers()
            finally:
                self.ws_clients.discard(websocket)
                self.onwsleave_handlers()
                Log.ws_clients = self.ws_clients

        async def start_server():
            async with websockets.serve(handler, self.host, self.ws_port):
                Log.server(f"WebSocket server started on {self.host}:{self.ws_port}")
                await asyncio.Future()

        def run_server():
            self.ws_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.ws_loop)
            Log.ws_loop = self.ws_loop
            self.ws_loop.run_until_complete(start_server())

        threading.Thread(target=run_server, daemon=True).start()

    def _execute_command(self, command: str):
        try:

            if "#" in command:
                command = command.split("#", 1)[0]

            command = command.strip()
            if not command:
                return True
            
            cmd = command.split()
            command = cmd[0].lower()

            if command == 'exit':
                self.kick_client("all", "The server is closing.")
                return False

            elif command == 'list':
                self.list_clients()
                return True

            elif command == 'upload':
                if len(cmd) < 3:
                    Log.error("Usage: upload <targets> <file>")
                    Log.info("Targets: 'all', client_id, hostname, or comma-separated list")
                    return True

                self.upload_file(cmd[1], cmd[2])
                return True

            elif command == 'start':
                if len(cmd) < 3:
                    Log.error("Usage: start <targets> <file> [freq] [loop] [ps] [rt] [pi]")
                    Log.info("Targets: 'all', client_id, hostname, or comma-separated list")
                    return True
                
                frequency = float(cmd[3]) if len(cmd) > 3 else 90.0
                loop = cmd[4].lower() == 'true' if len(cmd) > 4 else False
                ps = cmd[5] if len(cmd) > 5 else "BotWave"
                rt = cmd[6] if len(cmd) > 6 else "Broadcasting"
                pi = cmd[7] if len(cmd) > 7 else "FFFF"

                self.start_broadcast(cmd[1], cmd[2], frequency, ps, rt, pi, loop)
                return True

            elif command == 'stop':
                if len(cmd) < 2:
                    Log.error("Usage: stop <targets>")
                    Log.info("Targets: 'all', client_id, hostname, or comma-separated list")
                    return True

                self.stop_broadcast(cmd[1])
                return True
            
            elif command == 'sstv':
                if len(cmd) < 3:
                    Log.error("Usage: sstv <targets> <image_path> [mode] [output_wav] [frequency] [loop] [ps] [rt] [pi]")
                    return True

                targets = cmd[1]
                img_path = cmd[2]
                mode = cmd[3] if len(cmd) > 3 else None
                output_wav = cmd[4] if len(cmd) > 4 else os.path.splitext(os.path.basename(img_path))[0] + ".wav"
                frequency = float(cmd[5]) if len(cmd) > 5 else 90.0
                loop = cmd[6].lower() == 'true' if len(cmd) > 6 else False
                ps = cmd[7] if len(cmd) > 7 else "RADIOOOO"
                rt = cmd[8] if len(cmd) > 8 else "Broadcasting"
                pi = cmd[9] if len(cmd) > 9 else "FFFF"

                target_clients = self._parse_client_targets(targets)

                if not target_clients:
                    return False

                if not os.path.exists(img_path):
                    Log.error(f"Image file {img_path} not found")
                    return True

                Log.sstv(f"Generating SSTV WAV from {img_path} using mode {mode or 'auto'}...")

                success = make_sstv_wav(img_path, output_wav, mode)

                if success:
                    Log.sstv(f"Uploading {output_wav} to {targets}...")
                    self.upload_file(targets, output_wav)

                    Log.sstv(f"Broadcasting {os.path.basename(output_wav)} on {frequency} MHz to {targets}...")
                    self.start_broadcast(targets, output_wav, frequency, ps, rt, pi, loop)
                return True


            elif command == 'kick':
                if len(cmd) < 2:
                    Log.error("Usage: kick <targets> [reason]")
                    Log.info("Targets: 'all', client_id, hostname, or comma-separated list")
                    return True

                reason = " ".join(cmd[2:]) if len(cmd) > 2 else "Kicked by administrator"
                self.kick_client(cmd[1], reason)
                return True

            elif command == 'restart':
                if len(cmd) < 2:
                    Log.error("Usage: restart <targets>")
                    Log.info("Targets: 'all', client_id, hostname, or comma-separated list")
                    return True

                self.restart_client(cmd[1])
                return True

            elif command == 'handlers':
                if len(cmd) > 1:
                    filename = cmd[1]
                    self.handlers_executor.list_handler_commands(filename)
                else:
                    self.handlers_executor.list_handlers()
                return True
            
            elif command == '<':
                if len(cmd) < 2:
                    Log.error("Usage: < <shell command>")
                    return True
                shell_command = ' '.join(cmd[1:])
                self.run_shell_command(shell_command)
                return True
            
            elif command == 'dl':
                if len(cmd) < 3:
                    Log.error("Usage: dl <targets> <url>")
                    Log.info("Targets: 'all', client_id, hostname, or comma-separated list")
                    return True
                self.download_file(cmd[1], cmd[2])
                return True
            
            elif command == 'lf':
                if len(cmd) < 2:
                    Log.error("Usage: lf <targets>")
                    Log.info("Targets: 'all', client_id, hostname, or comma-separated list")
                    return True
                
                self.list_files(cmd[1])
                return True

            elif command == 'rm':
                if len(cmd) < 3:
                    Log.error("Usage: rm <targets> <filename|all>")
                    Log.info("Targets: 'all', client_id, hostname, or comma-separated list")
                    return True
                
                self.remove_file(cmd[1], cmd[2])
                return True
            
            elif command == 'sync':
                if len(cmd) < 3:
                    Log.error("Usage: sync <targets|folder/path/> <source_target|folder/path/>")
                    Log.info("Targets: 'all', client_id, hostname, comma-separated list, or local folder ending with /")
                    Log.info("Source: client_id, hostname, or local folder path ending with /")
                    return True
                
                self.sync_files(cmd[1], cmd[2])
                return True

            elif command == 'help':
                self.display_help()
                return True

            else:
                Log.error(f"Unknown command: {command}")
                Log.info("Type 'help' for a list of available commands")
                return True
        except Exception as e:
            Log.error(f"Error executing command '{command}': {e}")
            return True

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

    def run_shell_command(self, command: str):
        try:
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

            for line in process.stdout:
                Log.print(line, end='')

            return_code = process.wait()

            if return_code != 0:
                Log.info(f"STDERR (err {return_code}):")
                for line in process.stderr:
                    Log.print(line, end='')

                #Log.print(f"Command failed with return code {return_code}", "bright_red", "ERR", end='')
            
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
            Log.print(f"  Address: {client.addr[0]}:{client.addr[1]}", 'cyan')
            Log.print(f"  Protocol Version: {client.protocol_version}", 'cyan')
            Log.print(f"  Connected: {client.connected_at.strftime('%Y-%m-%d %H:%M:%S')}", 'cyan')
            Log.print(f"  Last seen: {client.last_seen.strftime('%Y-%m-%d %H:%M:%S')}", 'cyan')
            Log.print("")

    def upload_file(self, client_targets: str, file_path: str):
        if os.path.isdir(file_path):
            return self._upload_folder_contents(client_targets, file_path)

        if not os.path.exists(file_path):
            Log.error(f"File {file_path} not found")
            return False

        target_clients = self._parse_client_targets(client_targets)

        if not target_clients:
            return False

        try:
            with open(file_path, 'rb') as f:
                file_data = f.read()
        except Exception as e:
            Log.error(f"Error reading file: {e}")
            return False

        success_count = 0
        total_count = len(target_clients)
        file_size = len(file_data)

        # dynamic chunk sizing based on file size
        if file_size < 1024 * 1024:  # < 1MB
            chunk_size = 32768  # 32KB
        elif file_size < 10 * 1024 * 1024:  # < 10MB
            chunk_size = 131072  # 128KB
        elif file_size < 100 * 1024 * 1024:  # < 100MB
            chunk_size = 524288  # 512KB
        else:  # >= 100MB
            chunk_size = 1048576  # 1MB

        Log.broadcast(f"Uploading {os.path.basename(file_path)} to {total_count} client(s)... (chunk size: {chunk_size / 1024:.0f}KB)")

        for client_id in target_clients:
            if client_id not in self.clients:
                Log.error(f"  {client_id}: Client not found")
                continue

            client = self.clients[client_id]

            client.uploading = True

            try:
                command = {
                    "type": "upload_file",
                    "filename": os.path.basename(file_path),
                    "size": file_size
                }

                response = client.send_command(command)

                if response and response.get('status') == 'ready':
                    bytes_sent = 0
                    
                    while bytes_sent < file_size:
                        chunk = file_data[bytes_sent:bytes_sent + chunk_size]
                        client.conn.sendall(chunk)
                        bytes_sent += len(chunk)
                        Log.progress_bar(bytes_sent, file_size, prefix=f"{os.path.basename(file_path)} {client.get_display_name()}:", suffix="Complete", style="yellow", icon='FILE', auto_clear=False)

                    Log.progress_bar(file_size, file_size, prefix=f"{os.path.basename(file_path)} {client.get_display_name()}", suffix="Complete", style="yellow", icon='FILE')

                    try:
                        confirm_buffer = ""
                        client.conn.settimeout(10)  # 10 second timeout for confirmation
                        
                        while '\n' not in confirm_buffer:
                            data = client.conn.recv(1024).decode('utf-8')
                            if not data:
                                raise Exception("Connection closed while waiting for confirmation")
                            confirm_buffer += data
                        
                        confirm_line = confirm_buffer.split('\n', 1)[0].strip()
                        
                        if not confirm_line:
                            raise Exception("Empty confirmation received")
                        
                        confirm_json = json.loads(confirm_line)

                        if confirm_json.get('status') == 'uploaded':
                            Log.success(f"  {client.get_display_name()}: Upload successful")
                            success_count += 1
                        else:
                            Log.error(f"  {client.get_display_name()}: {confirm_json.get('message', 'Unknown error')}")

                        client.uploading = False
                        
                            
                    except json.JSONDecodeError as e:
                        Log.clear_progress_bar()
                        Log.error(f"  {client.get_display_name()}: Invalid JSON in confirmation - {e}")
                    except socket.timeout:
                        Log.clear_progress_bar()
                        Log.error(f"  {client.get_display_name()}: Timeout waiting for confirmation")
                    except Exception as e:
                        Log.clear_progress_bar()
                        Log.error(f"  {client.get_display_name()}: Error receiving confirmation - {e}")
                    finally:
                        client.uploading = False
                        client.conn.settimeout(None)
                else:
                    Log.error(f"  {client.get_display_name()}: {response.get('message') if response else 'No response'}")
            except Exception as e:
                Log.error(f"  {client.get_display_name()}: Error - {e}")

        Log.broadcast(f"Upload completed: {success_count}/{total_count} successful")
        return success_count > 0
    
    def _upload_folder_contents(self, client_targets: str, folder_path: str):
        # Upload all WAV files from a folder to target clients.

        # chosen to not use compression to support even lightest clients, even if it takes more time overall.

        if not os.path.exists(folder_path):
            Log.error(f"Folder {folder_path} not found")
            return False
        
        if not os.path.isdir(folder_path):
            Log.error(f"{folder_path} is not a directory")
            return False
        
        # this isnt recursive 
        wav_files = [f for f in os.listdir(folder_path) 
                    if f.lower().endswith('.wav') and os.path.isfile(os.path.join(folder_path, f))]
        
        if not wav_files:
            Log.warning(f"No WAV files found in {folder_path}")
            return False
        
        Log.broadcast(f"Found {len(wav_files)} WAV file(s) in {folder_path}")
        
        overall_success = 0
        total_files = len(wav_files)
        
        for idx, filename in enumerate(wav_files, 1):
            full_path = os.path.join(folder_path, filename)
            Log.file(f"[{idx}/{total_files}] Processing {filename}...")
            
            if self.upload_file(client_targets, full_path):
                overall_success += 1
            
            # small delay between uploads to prevent overwhelming clients
            if idx < total_files:
                time.sleep(0.5)
        
        Log.broadcast(f"Folder upload completed: {overall_success}/{total_files} files uploaded successfully")
        return overall_success > 0
    
    
    def download_file(self, client_targets: str, url: str):
        target_clients = self._parse_client_targets(client_targets)
        if not target_clients:
            return False

        command = {
            "type": "download_file",
            "url": url
        }

        success_count = 0
        total_count = len(target_clients)
        Log.broadcast(f"Requesting download from {total_count} client(s)...")

        for client_id in target_clients:
            if client_id not in self.clients:
                Log.error(f"  {client_id}: Client not found")
                continue

            client = self.clients[client_id]
            response = client.send_command(command)

            if response and response.get('status') == 'success':
                Log.success(f"  {client.get_display_name()}: Download successful")
                success_count += 1
            else:
                Log.error(f"  {client.get_display_name()}: {response.get('message', 'Unknown error')}")

        Log.broadcast(f"Download request completed: {success_count}/{total_count} successful")
        return success_count > 0
    

    def remove_file(self, client_targets: str, filename: str):
        target_clients = self._parse_client_targets(client_targets)

        if not target_clients:
            return False
        
        command = {
            "type": "remove_file",
            "filename": filename
        }

        success_count = 0
        total_count = len(target_clients)

        Log.broadcast(f"Removing file '{filename}' from {total_count} client(s)...")
        for client_id in target_clients:
            if client_id not in self.clients:
                Log.error(f"  {client_id}: Client not found")
                continue

            client = self.clients[client_id]
            response = client.send_command(command)

            if response and response.get('status') == 'success':
                Log.success(f"  {client.get_display_name()}: File removed")
                success_count += 1

            else:
                Log.error(f"  {client.get_display_name()}: {response.get('message', 'Unknown error')}")

        Log.broadcast(f"File removal completed: {success_count}/{total_count} successful")
        return success_count > 0
    
    def sync_files(self, client_targets: str, source: str):
        # Sync files between clients and/or local folders.
        # 
        # Supports:
        # - sync <clients> <source_client> - Sync from one client to others
        # - sync <clients> <folder/> - Sync from local folder to clients
        # - sync <folder/> <source_client> - Sync from client to local folder
        
        
        is_target_folder = client_targets.endswith('/')
        is_source_folder = source.endswith('/')
        
        # Case 1: Sync FROM client TO local folder
        if is_target_folder and not is_source_folder:
            return self._sync_client_to_folder(client_targets.rstrip('/'), source)
        
        # Case 2: Sync TO clients (from folder or another client)
        target_clients = self._parse_client_targets(client_targets)
        
        if not target_clients:
            return False
        
        # determine source and get files
        temp_dir = None
        source_dir = None
        source_client_id = None
        
        if is_source_folder:
            source_dir = source.rstrip('/')
            if not os.path.exists(source_dir) or not os.path.isdir(source_dir):
                Log.error(f"Source folder {source_dir} not found")
                return False
            
            wav_files = [f for f in os.listdir(source_dir) 
                        if f.lower().endswith('.wav') and os.path.isfile(os.path.join(source_dir, f))]
            
            if not wav_files:
                Log.warning(f"No WAV files found in {source_dir}")
                return False
            
            Log.broadcast(f"Syncing from local folder: {source_dir} ({len(wav_files)} files)")
        else:
            # client - fetch files to a temp dir
            source_clients = self._parse_client_targets(source)
            
            if not source_clients or len(source_clients) != 1:
                Log.error(f"Source '{source}' must resolve to exactly one client")
                return False
            
            source_client_id = source_clients[0]
            
            if source_client_id not in self.clients:
                Log.error(f"Source client {source_client_id} not found")
                return False
            
            temp_dir = tempfile.mkdtemp(prefix='botwave_sync_')
            source_dir = temp_dir
            
            Log.broadcast(f"Fetching files from source client: {source_client_id}")
            
            source_client = self.clients[source_client_id]
            if not self._download_files_from_client(source_client, temp_dir):
                if temp_dir:
                    self._remove_temp_dir(temp_dir)
                return False
        
        Log.broadcast(f"Clearing files from {len(target_clients)} target client(s)...")
        
        for client_id in target_clients:
            if client_id == source_client_id:
                Log.info(f"  Skipping source client: {client_id}")
                continue
            
            if client_id not in self.clients:
                Log.error(f"  {client_id}: Client not found")
                continue
            
            remove_response = self.clients[client_id].send_command({
                "type": "remove_file",
                "filename": "all"
            })
            
            if remove_response and remove_response.get('status') == 'success':
                Log.success(f"  {self.clients[client_id].get_display_name()}: Files cleared")
            else:
                Log.warning(f"  {self.clients[client_id].get_display_name()}: Clear failed")
        
        Log.broadcast(f"Uploading synchronized files to targets...")
        
        sync_targets = [cid for cid in target_clients if cid != source_client_id]
        
        if not sync_targets:
            Log.warning("No targets to sync to (all targets were the source)")
            if temp_dir:
                self._remove_temp_dir(temp_dir)
            return True
        
        success = self._upload_folder_contents(','.join(sync_targets), source_dir)
        
        if temp_dir:
            self._remove_temp_dir(temp_dir)
            Log.info("Cleaned up temporary files")
        
        if success:
            Log.broadcast(f"Sync completed successfully!")
        else:
            Log.error("Sync completed with errors")
        
        return success


    def _sync_client_to_folder(self, target_dir: str, source: str):
        # Download all files from a client to a local folder.
        
        # Validate/create target directory
        if not os.path.exists(target_dir):
            Log.error(f"Directory doesn't exists: {target_dir}")
            return False
        

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
        
        success = self._download_files_from_client(source_client, target_dir)
        
        if success:
            Log.broadcast(f"Sync to local folder completed successfully!")
        else:
            Log.error("Sync to local folder completed with errors")
        
        return success


    def _download_files_from_client(self, client: 'BotWaveClient', dest_dir: str) -> bool:
        # Download all files from a client to a destination directory.
        
        # get list of files from client
        list_response = client.send_command({"type": "list_files"})
        
        if not list_response or list_response.get('status') != 'success':
            Log.error(f"Failed to get file list from {client.get_display_name()}")
            return False
        
        files = list_response.get('files', [])
        
        if not files:
            Log.warning(f"{client.get_display_name()} has no files to download")
            return False
        
        Log.broadcast(f"Downloading {len(files)} file(s) from {client.get_display_name()}...")
        
        success_count = 0
        
        for file_info in files:
            filename = file_info.get('name')
            
            Log.file(f"  Requesting {filename}...")
            
            client.uploading = True
            
            send_cmd = {
                "type": "send_file",
                "filename": filename
            }
            
            response = client.send_command(send_cmd)
            
            if response and response.get('status') == 'ready':
                file_size = response.get('size', 0)
                file_path = os.path.join(dest_dir, filename)
                
                try:
                    # Dynamic chunk sizing
                    if file_size < 1024 * 1024:
                        chunk_size = 32768
                    elif file_size < 10 * 1024 * 1024:
                        chunk_size = 131072
                    elif file_size < 100 * 1024 * 1024:
                        chunk_size = 524288
                    else:
                        chunk_size = 1048576
                    
                    Log.file(f"  Receiving {filename}... (chunk size: {chunk_size / 1024:.0f}KB)")
                    
                    original_timeout = client.conn.gettimeout()
                    transfer_timeout = max(60, file_size / 100000)
                    client.conn.settimeout(transfer_timeout)
                    
                    received_data = b''
                    
                    while len(received_data) < file_size:
                        try:
                            remaining = file_size - len(received_data)
                            current_chunk_size = min(chunk_size, remaining)
                            
                            chunk = client.conn.recv(current_chunk_size)
                            if not chunk:
                                Log.error("Connection closed during file transfer")
                                break
                            
                            received_data += chunk
                            
                            if file_size > 1024 * 1024:
                                Log.progress_bar(len(received_data), file_size, 
                                            prefix=f'{filename}', suffix='Complete', 
                                            style='yellow', icon='FILE', auto_clear=False)
                        
                        except socket.timeout:
                            Log.error("Timeout while receiving file data")
                            break
                        except Exception as e:
                            Log.error(f"Error receiving file chunk: {e}")
                            break
                    
                    if file_size > 1024 * 1024:
                        Log.progress_bar(file_size, file_size, prefix=f'{filename}:', 
                                    suffix='Complete', style='yellow', icon='FILE')
                    
                    if len(received_data) != file_size:
                        Log.error(f"  Incomplete transfer: received {len(received_data)}/{file_size} bytes")
                        client.conn.settimeout(original_timeout)
                        client.uploading = False
                        continue
                    
                    # Write to file
                    with open(file_path, 'wb') as f:
                        f.write(received_data)
                    
                    confirm_response = {"status": "received", "message": "File received successfully"}
                    client.conn.sendall((json.dumps(confirm_response) + '\n').encode('utf-8'))
                    
                    Log.success(f"  Downloaded {filename} ({len(received_data)} bytes)")
                    success_count += 1
                    
                    client.conn.settimeout(original_timeout)
                    client.uploading = False
                    
                except Exception as e:
                    Log.error(f"  Failed to download {filename}: {e}")
                    client.uploading = False
                    try:
                        error_response = {"status": "error", "message": f"Transfer error: {str(e)}"}
                        client.conn.sendall((json.dumps(error_response) + '\n').encode('utf-8'))
                    except:
                        pass
            else:
                error_msg = response.get('message', 'Unknown error') if response else 'No response'
                Log.error(f"  Client couldn't prepare {filename}: {error_msg}")
                client.uploading = False
        
        return success_count > 0

    def _remove_temp_dir(self, directory: str):
        try:
            os.rmdir(directory)
        except Exception as e:
            Log.warning(f"Failed to remove temp directory {directory}: {e}")

    def start_broadcast(self, client_targets: str, filename: str, frequency: float = 90.0,
                       ps: str = "RADIOOOO", rt: str = "Broadcasting since 2025", pi: str = "FFFF",
                       loop: bool = False):
        target_clients = self._parse_client_targets(client_targets)

        if not target_clients:
            return False

        if self.wait_start and len(target_clients) > 1:
            start_at = datetime.now(timezone.utc).timestamp() + 20 * (len(target_clients) - 1)
            Log.broadcast(f"Starting broadcast at {datetime.fromtimestamp(start_at)}")
        else:
            start_at = 0
            Log.broadcast(f"Starting broadcast as soon as possible.")

        command = {
            "type": "start_broadcast",
            "filename": filename,
            "frequency": frequency,
            "ps": ps,
            "rt": rt,
            "pi": pi,
            "loop": loop,
            "start_at": start_at
        }

        success_count = 0
        total_count = len(target_clients)

        Log.broadcast(f"Starting broadcast on {total_count} client(s)...")

        for client_id in target_clients:
            if client_id not in self.clients:
                Log.error(f"  {client_id}: Client not found")
                continue

            client = self.clients[client_id]
            response = client.send_command(command)

            if response and response.get('status') == 'success':
                Log.success(f"  {client.get_display_name()}: Broadcasting started")
                success_count += 1
            else:
                Log.error(f"  {client.get_display_name()}: {response.get('message', 'Unknown error')}")

        Log.broadcast(f"Broadcast start completed: {success_count}/{total_count} successful")
        self.onstart_handlers()
        return success_count > 0

    def stop_broadcast(self, client_targets: str):
        target_clients = self._parse_client_targets(client_targets)

        if not target_clients:
            return False

        command = {"type": "stop_broadcast"}
        success_count = 0
        total_count = len(target_clients)

        Log.broadcast(f"Stopping broadcast on {total_count} client(s)...")

        for client_id in target_clients:
            if client_id not in self.clients:
                Log.error(f"  {client_id}: Client not found")
                continue

            client = self.clients[client_id]
            response = client.send_command(command)

            if response and response.get('status') == 'success':
                Log.success(f"  {client.get_display_name()}: Broadcasting stopped")
                success_count += 1
            else:
                Log.error(f"  {client.get_display_name()}: {response.get('message', 'Unknown error')}")

        Log.broadcast(f"Broadcast stop completed: {success_count}/{total_count} successful")
        self.onstop_handlers()
        return success_count > 0

    def kick_client(self, client_targets: str, reason: str = "Kicked by administrator"):
        target_clients = self._parse_client_targets(client_targets)

        if not target_clients:
            return False

        success_count = 0
        total_count = len(target_clients)

        Log.client(f"Kicking {total_count} client(s)...")

        for client_id in target_clients:
            if client_id not in self.clients:
                Log.error(f"  {client_id}: Client not found")
                continue

            client = self.clients[client_id]

            try:
                command = {
                    "type": "kick",
                    "reason": reason
                }

                client.send_command(command)
                client.conn.close()
                del self.clients[client_id]

                Log.success(f"  {client.get_display_name()}: Kicked - {reason}")
                success_count += 1
            except Exception as e:
                Log.error(f"  {client.get_display_name()}: Error kicking - {e}")

        Log.client(f"Kick completed: {success_count}/{total_count} successful")
        self.ondisconnect_handlers()
        return success_count > 0

    def restart_client(self, client_targets: str):
        target_clients = self._parse_client_targets(client_targets)

        if not target_clients:
            return False

        command = {"type": "restart"}
        success_count = 0
        total_count = len(target_clients)

        Log.client(f"Requesting restart from {total_count} client(s)...")

        for client_id in target_clients:
            if client_id not in self.clients:
                Log.error(f"  {client_id}: Client not found")
                continue

            client = self.clients[client_id]
            response = client.send_command(command)

            if response and response.get('status') == 'success':
                Log.success(f"  {client.get_display_name()}: Restart requested")
                success_count += 1
            else:
                Log.error(f"  {client.get_display_name()}: {response.get('message', 'Unknown error')}")

        Log.client(f"Restart request completed: {success_count}/{total_count} successful")
        return success_count > 0

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

    def stop(self):
        self.running = False

        if self.server_socket:
            self.server_socket.close()

        Log.server("Server stopped")

    def list_files(self, client_targets: str): #broadcastable files (WAVS) listing
        target_clients = self._parse_client_targets(client_targets)
        
        if not target_clients:
            return False
        
        command = {
            "type": "list_files"
        }
        
        success_count = 0
        total_count = len(target_clients)
        
        Log.info(f"Listing broadcastable files from {total_count} client(s)")
        
        for client_id in target_clients:
            if client_id not in self.clients:
                Log.error(f"  {client_id}: Client not found")
                continue
            
            client = self.clients[client_id]
            response = client.send_command(command)
            
            if response and response.get('status') == 'success':
                files = response.get('files', [])
                file_count = len(files)
                
                Log.success(f"  {client.get_display_name()}: {file_count} broadcastable files found")
                
                if files:
                    for file_info in files:
                        filename = file_info.get('name', 'unknown')
                        size = file_info.get('size', 0)
                        modified = file_info.get('modified', 'unknown')
                        
                        # format
                        if size < 1024:
                            size_str = f"{size} B"
                        elif size < 1024 * 1024:
                            size_str = f"{size / 1024:.1f} KB"
                        else:
                            size_str = f"{size / (1024 * 1024):.1f} MB"
                        
                        Log.print(f"    {filename} ({size_str}) - {modified}", 'white')
                else:
                    Log.print("    No WAV files found", 'yellow')
                
                success_count += 1
            else:
                error_msg = response.get('message', 'Unknown error') if response else 'No response'
                Log.error(f"  {client.get_display_name()}: {error_msg}")
        
        Log.info(f"File listing completed: {success_count}/{total_count} successful")
        return success_count > 0

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

        Log.print("upload <targets> <file|folder>", 'bright_green')
        Log.print("  Upload a WAV file or a folder's files to client(s)", 'white')
        Log.print("  Example: upload all broadcast.wav", 'cyan')
        Log.print("  Example: upload pi1,pi2 /home/bw/lib", 'cyan')
        Log.print("")

        Log.print("sync <targets|folder/> <source_target|folder/>", 'bright_green')
        Log.print("  Synchronize files across clients or to/from local folders", 'white')
        Log.print("  Source can be a client or a local folder path ending with /", 'white')
        Log.print("  Target can be clients or a local folder path ending with /", 'white')
        Log.print("  Example: sync all pi1", 'cyan')
        Log.print("  Example: sync pi2,pi3,pi4 /home/bw/lib/", 'cyan')
        Log.print("  Example: sync /home/bw/backup/ pi1", 'cyan')
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
    parser = argparse.ArgumentParser(description='BotWave - Server')

    parser.add_argument('--host', default='0.0.0.0', help='Server host')
    parser.add_argument('--port', type=int, default=9938, help='Server port')
    parser.add_argument('--pk', help='Optional passkey for authentication')
    parser.add_argument('--handlers-dir', default='/opt/BotWave/handlers', help='Directory to retrive l_ handlers from')
    parser.add_argument('--skip-update-check', action='store_true', help='Skip checking for protocol updates')
    parser.add_argument('--start-asap', action='store_false', help='Starts broadcasting as soon as possible. Can cause delay between different clients broadcasts.')
    parser.add_argument('--ws', type=int, help='WebSocket port')
    parser.add_argument('--daemon', action='store_true', help='Run in daemon mode (non-interactive, requires --ws port)')

    args = parser.parse_args()

    Log.header("BotWave - Server")

    server = BotWaveServer(args.host, args.port, args.pk, args.start_asap, args.ws, args.daemon)
    server.start()
    server.onready_handlers(args.handlers_dir)

    if not args.daemon:
        Log.print("Type 'help' for a list of available commands", 'bright_yellow')

        try:
            while True:
                try:
                    print()
                    cmd_input = input("\033[1;32mbotwave ›\033[0m ").strip()

                    if not cmd_input:
                        continue

                    server.command_history.append(cmd_input)
                    server.history_index = len(server.command_history)
                    exit = server._execute_command(cmd_input)

                    if not exit:
                        break
                except KeyboardInterrupt:
                    Log.warning("Use 'exit' to exit")
                except EOFError:
                    Log.server("Exiting...")
                    break
                except Exception as e:
                    Log.error(f"Error: {e}")
        finally:
            server.stop()
    else:
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            server.stop()

if __name__ == "__main__":
    main()
