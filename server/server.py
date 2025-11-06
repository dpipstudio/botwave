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
import urllib.request
import urllib.error
import asyncio
import websockets
from datetime import datetime, timezone
from typing import Dict, List, Optional
import subprocess

PROTOCOL_VERSION = "1.0.2" # if mismatch of 1th or 2th part: error
VERSION_CHECK_URL = "https://botwave.dpip.lol/api/latestpro/" # to retrieve the lastest ver

class Log:
    COLORS = { # absolutely not taken from stackoverflow trust
        'reset': '\033[0m',
        'bold': '\033[1m',
        'underline': '\033[4m',
        'red': '\033[31m',
        'green': '\033[32m',
        'yellow': '\033[33m',
        'blue': '\033[34m',
        'magenta': '\033[35m',
        'cyan': '\033[36m',
        'white': '\033[37m',
        'bright_red': '\033[91m',
        'bright_green': '\033[92m',
        'bright_yellow': '\033[93m',
        'bright_blue': '\033[94m',
        'bright_magenta': '\033[95m',
        'bright_cyan': '\033[96m',
        'bright_white': '\033[97m',
    }

    ICONS = {
        'success': 'OK',
        'error': 'ERR',
        'warning': 'WARN',
        'info': 'INFO',
        'client': 'CLIENT',
        'server': 'SERVER',
        'file': 'FILE',
        'broadcast': 'BCAST',
        'version': 'VER',
        'update': 'UPD',
        'handler': 'HNDL',
    }

    ws_clients = set()
    ws_loop = None

    @classmethod
    def set_ws_clients(cls, clients):
        cls.ws_clients = clients

    @classmethod
    def print(cls, message: str, style: str = '', icon: str = '', end: str = '\n'):
        color = cls.COLORS.get(style, '')
        icon_char = cls.ICONS.get(icon, '')

        if icon_char:
            if color:
                print(f"{color}[{icon_char}]\033[0m {message}", end=end)
            else:
                print(f"[{icon_char}] {message}", end=end)
        else:
            if color:
                print(f"{color}{message}\033[0m", end=end)
            else:
                print(f"{message}", end=end)

        sys.stdout.flush()

        ws_message = f"[{icon_char}] {message}" if icon_char else message

        for ws in list(cls.ws_clients):
            try:
                if cls.ws_loop:
                    asyncio.run_coroutine_threadsafe(ws.send(ws_message), cls.ws_loop)
            except Exception as e:
                print(f"Error sending to WebSocket client: {e}")
                try:
                    cls.ws_clients.discard(ws)
                except Exception:
                    pass

    @classmethod
    def header(cls, text: str):
        cls.print(text, 'bright_blue', end='\n\n')
        sys.stdout.flush()

    @classmethod
    def section(cls, text: str):
        cls.print(f" {text} ", 'bright_blue', end='')
        cls.print("─" * (len(text) + 2), 'blue', end='\n\n')
        sys.stdout.flush()

    @classmethod
    def success(cls, message: str):
        cls.print(message, 'bright_green', 'success')

    @classmethod
    def error(cls, message: str):
        cls.print(message, 'bright_red', 'error')

    @classmethod
    def warning(cls, message: str):
        cls.print(message, 'bright_yellow', 'warning')

    @classmethod
    def info(cls, message: str):
        cls.print(message, 'bright_cyan', 'info')

    @classmethod
    def client_message(cls, message: str):
        cls.print(message, 'magenta', 'client')

    @classmethod
    def server_message(cls, message: str):
        cls.print(message, 'cyan', 'server')

    @classmethod
    def file_message(cls, message: str):
        cls.print(message, 'yellow', 'file')

    @classmethod
    def broadcast_message(cls, message: str):
        cls.print(message, 'bright_magenta', 'broadcast')

    @classmethod
    def version_message(cls, message: str):
        cls.print(message, 'bright_cyan', 'version')

    @classmethod
    def update_message(cls, message: str):
        cls.print(message, 'bright_yellow', 'update')

    @classmethod
    def handler_message(cls, message: str):
        cls.print(message, 'magenta', 'handler')

def parse_version(version_str: str) -> tuple:
    try:
        return tuple(map(int, version_str.split('.')))
    except (ValueError, AttributeError):
        return (0, 0, 0)

def check_for_updates(current_version: str, check_url: str) -> Optional[str]:
    try:
        with urllib.request.urlopen(check_url, timeout=10) as response:
            remote_version = response.read().decode('utf-8').strip()

        current_tuple = parse_version(current_version)
        remote_tuple = parse_version(remote_version)

        if remote_tuple > current_tuple:
            return remote_version

        return None
    except (urllib.error.URLError, urllib.error.HTTPError, Exception):
        return None

def versions_compatible(server_version: str, client_version: str) -> bool:
    server_tuple = parse_version(server_version)
    client_tuple = parse_version(client_version)
    return server_tuple[:2] == client_tuple[:2]

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

    def start(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(10)
            self.running = True

            Log.server_message(f"BotWave Server started on {self.host}:{self.port}")
            Log.version_message(f"Protocol Version: {PROTOCOL_VERSION}")

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
            latest_version = check_for_updates(PROTOCOL_VERSION, VERSION_CHECK_URL)

            if latest_version:
                Log.update_message(f"Update available! Latest version: {latest_version}")
                Log.update_message("Consider updating to the latest version by running 'bw-update' in your shell.")
            else:
                Log.success("You are using the latest protocol version")
        except Exception as e:
            Log.warning("Unable to check for updates (continuing anyway)")

    def _accept_clients(self):
        while self.running:
            try:
                conn, addr = self.server_socket.accept()
                Log.client_message(f"New connection from {addr[0]}:{addr[1]}")
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
                Log.version_message(f"  Client protocol version: {client_protocol_version}")

                self.onconnect_handlers()
                self._keep_client_alive(client_id)
        except Exception as e:
            Log.error(f"Error handling client {addr[0]}:{addr[1]}: {e}")
            conn.close()

    def _keep_client_alive(self, client_id: str):
        while self.running and client_id in self.clients:
            try:
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
            Log.set_ws_clients(self.ws_clients)

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
                    Log.client_message(f"WebSocket CMD: {message}")

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
                                self.list_handler_commands(filename)
                            else:
                                self.list_handlers()
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
                Log.set_ws_clients(self.ws_clients)

        async def start_server():
            async with websockets.serve(handler, self.host, self.ws_port):
                Log.server_message(f"WebSocket server started on {self.host}:{self.ws_port}")
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
                    self.list_handler_commands(filename)
                else:
                    self.list_handlers()
                return True
            
            elif command == '<':
                if len(cmd) < 2:
                    Log.error("Usage: > <shell command>")
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
        if dir_path is None:
            dir_path = self.handlers_dir
        if not os.path.exists(dir_path):
            Log.error(f"Directory {dir_path} not found")
            return False
        for filename in os.listdir(dir_path):
            if filename.endswith(".hdl") and filename.startswith("s_onready"):
                file_path = os.path.join(dir_path, filename)
                self._execute_handler(file_path, silent=False)
            elif filename.endswith(".shdl") and filename.startswith("s_onready"):
                file_path = os.path.join(dir_path, filename)
                self._execute_handler(file_path, silent=True)

    def onstart_handlers(self, dir_path: str = None):
        if dir_path is None:
            dir_path = self.handlers_dir
        if not os.path.exists(dir_path):
            Log.error(f"Directory {dir_path} not found")
            return False
        for filename in os.listdir(dir_path):
            if filename.endswith(".hdl") and filename.startswith("s_onstart"):
                file_path = os.path.join(dir_path, filename)
                self._execute_handler(file_path, silent=False)
            elif filename.endswith(".shdl") and filename.startswith("s_onstart"):
                file_path = os.path.join(dir_path, filename)
                self._execute_handler(file_path, silent=True)

    def onstop_handlers(self, dir_path: str = None):
        if dir_path is None:
            dir_path = self.handlers_dir
        if not os.path.exists(dir_path):
            Log.error(f"Directory {dir_path} not found")
            return False
        for filename in os.listdir(dir_path):
            if filename.endswith(".hdl") and filename.startswith("s_onstop"):
                file_path = os.path.join(dir_path, filename)
                self._execute_handler(file_path, silent=False)
            elif filename.endswith(".shdl") and filename.startswith("s_onstop"):
                file_path = os.path.join(dir_path, filename)
                self._execute_handler(file_path, silent=True)

    def onconnect_handlers(self, dir_path: str = None):
        if dir_path is None:
            dir_path = self.handlers_dir
        if not os.path.exists(dir_path):
            Log.error(f"Directory {dir_path} not found")
            return False
        for filename in os.listdir(dir_path):
            if filename.endswith(".hdl") and filename.startswith("s_onconnect"):
                file_path = os.path.join(dir_path, filename)
                self._execute_handler(file_path, silent=False)
            elif filename.endswith(".shdl") and filename.startswith("s_onconnect"):
                file_path = os.path.join(dir_path, filename)
                self._execute_handler(file_path, silent=True)

    def ondisconnect_handlers(self, dir_path: str = None):
        if dir_path is None:
            dir_path = self.handlers_dir
        if not os.path.exists(dir_path):
            Log.error(f"Directory {dir_path} not found")
            return False
        for filename in os.listdir(dir_path):
            if filename.endswith(".hdl") and filename.startswith("s_ondisconnect"):
                file_path = os.path.join(dir_path, filename)
                self._execute_handler(file_path, silent=False)
            elif filename.endswith(".shdl") and filename.startswith("s_ondisconnect"):
                file_path = os.path.join(dir_path, filename)
                self._execute_handler(file_path, silent=True)

    def onwsjoin_handlers(self, dir_path: str = None):
        if dir_path is None:
            dir_path = self.handlers_dir
        if not os.path.exists(dir_path):
            Log.error(f"Directory {dir_path} not found")
            return False
        for filename in os.listdir(dir_path):
            if filename.endswith(".hdl") and filename.startswith("s_onwsjoin"):
                file_path = os.path.join(dir_path, filename)
                self._execute_handler(file_path, silent=False)
            elif filename.endswith(".shdl") and filename.startswith("s_onwsjoin"):
                file_path = os.path.join(dir_path, filename)
                self._execute_handler(file_path, silent=True)

    def onwsleave_handlers(self, dir_path: str = None):
        if dir_path is None:
            dir_path = self.handlers_dir
        if not os.path.exists(dir_path):
            Log.error(f"Directory {dir_path} not found")
            return False
        for filename in os.listdir(dir_path):
            if filename.endswith(".hdl") and filename.startswith("s_onwsleave"):
                file_path = os.path.join(dir_path, filename)
                self._execute_handler(file_path, silent=False)
            elif filename.endswith(".shdl") and filename.startswith("s_onwsleave"):
                file_path = os.path.join(dir_path, filename)
                self._execute_handler(file_path, silent=True)

    def _execute_handler(self, file_path: str, silent: bool = False):
        try:
            if not silent:
                Log.handler_message(f"Running handler on {file_path}")
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()

                    if line:
                        if line[0] != "#":
                            if not silent:
                                Log.handler_message(f"Executing command: {line}")
                            self._execute_command(line)
        except Exception as e:
            Log.error(f"Error executing command from {file_path}: {e}")

    def run_shell_command(self, command: str):
        try:
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

            for line in process.stdout:
                Log.print(line, end='')

            return_code = process.wait()

            if return_code != 0:
                for line in process.stderr:
                    Log.error(line, end='')
                Log.error(f"Command failed with return code {return_code}")
            
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

        Log.broadcast_message(f"Uploading {os.path.basename(file_path)} to {total_count} client(s)...")

        for client_id in target_clients:
            if client_id not in self.clients:
                Log.error(f"  {client_id}: Client not found")
                continue

            client = self.clients[client_id]

            try:
                command = {
                    "type": "upload_file",
                    "filename": os.path.basename(file_path),
                    "size": len(file_data)
                }

                response = client.send_command(command)

                if response and response.get('status') == 'ready':
                    client.conn.sendall(file_data)

                    try:
                        confirm_data = client.conn.recv(4096).decode('utf-8').strip()
                        confirm_json = json.loads(confirm_data)

                        if confirm_json.get('status') == 'uploaded':
                            Log.success(f"  {client.get_display_name()}: Upload successful")
                            success_count += 1
                        else:
                            Log.error(f"  {client.get_display_name()}: {confirm_json.get('message', 'Unknown error')}")
                    except Exception as e:
                        Log.error(f"  {client.get_display_name()}: Error receiving confirmation - {e}")
                else:
                    Log.error(f"  {client.get_display_name()}: {response.get('message') if response else 'No response'}")
            except Exception as e:
                Log.error(f"  {client.get_display_name()}: Error - {e}")

        Log.broadcast_message(f"Upload completed: {success_count}/{total_count} successful")
        return success_count > 0
    
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
        Log.broadcast_message(f"Requesting download from {total_count} client(s)...")

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

        Log.broadcast_message(f"Download request completed: {success_count}/{total_count} successful")
        return success_count > 0


    def start_broadcast(self, client_targets: str, filename: str, frequency: float = 90.0,
                       ps: str = "RADIOOOO", rt: str = "Broadcasting since 2025", pi: str = "FFFF",
                       loop: bool = False):
        target_clients = self._parse_client_targets(client_targets)

        if not target_clients:
            return False

        if self.wait_start and len(target_clients) > 1:
            start_at = datetime.now(timezone.utc).timestamp() + 20 * (len(target_clients) - 1)
            Log.broadcast_message(f"Starting broadcast at {datetime.fromtimestamp(start_at)}")
        else:
            start_at = 0
            Log.broadcast_message(f"Starting broadcast as soon as possible.")

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

        Log.broadcast_message(f"Starting broadcast on {total_count} client(s)...")

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

        Log.broadcast_message(f"Broadcast start completed: {success_count}/{total_count} successful")
        self.onstart_handlers()
        return success_count > 0

    def stop_broadcast(self, client_targets: str):
        target_clients = self._parse_client_targets(client_targets)

        if not target_clients:
            return False

        command = {"type": "stop_broadcast"}
        success_count = 0
        total_count = len(target_clients)

        Log.broadcast_message(f"Stopping broadcast on {total_count} client(s)...")

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

        Log.broadcast_message(f"Broadcast stop completed: {success_count}/{total_count} successful")
        self.onstop_handlers()
        return success_count > 0

    def kick_client(self, client_targets: str, reason: str = "Kicked by administrator"):
        target_clients = self._parse_client_targets(client_targets)

        if not target_clients:
            return False

        success_count = 0
        total_count = len(target_clients)

        Log.client_message(f"Kicking {total_count} client(s)...")

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

        Log.client_message(f"Kick completed: {success_count}/{total_count} successful")
        self.ondisconnect_handlers()
        return success_count > 0

    def restart_client(self, client_targets: str):
        target_clients = self._parse_client_targets(client_targets)

        if not target_clients:
            return False

        command = {"type": "restart"}
        success_count = 0
        total_count = len(target_clients)

        Log.client_message(f"Requesting restart from {total_count} client(s)...")

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

        Log.client_message(f"Restart request completed: {success_count}/{total_count} successful")
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

        Log.server_message("Server stopped")

    def list_handlers(self, dir_path: str = "/opt/BotWave/handlers"):
        if not os.path.exists(dir_path):
            Log.error(f"Directory {dir_path} not found")
            return False

        try:
            handlers = [f for f in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, f))]

            if not handlers:
                Log.info(f"No handlers found in the directory {dir_path}")
                return

            Log.info(f"Handlers in directory {dir_path}:")

            for handler in handlers:
                Log.print(f"  {handler}", 'white')
        except Exception as e:
            Log.error(f"Error listing handlers: {e}")

    def list_handler_commands(self, filename: str, dir_path: str = "/opt/BotWave/handlers"):
        file_path = os.path.join(dir_path, filename)

        if not os.path.exists(file_path):
            Log.error(f"Handler file {filename} not found")
            return False

        try:
            Log.info(f"Commands in handler file {filename}:")

            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()

                    if line:
                        Log.print(f"  {line}", 'white')
        except Exception as e:
            Log.error(f"Error listing commands from {filename}: {e}")

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

        Log.print("upload <targets> <file>", 'bright_green')
        Log.print("  Upload a WAV file to client(s)", 'white')
        Log.print("  Example: upload all broadcast.wav", 'cyan')
        Log.print("")

        Log.print("dl <targets> <url>", 'bright_green')
        Log.print("  Request client(s) to download a file from a URL", 'white')
        Log.print("  Example: dl all http://example.com/file.wav", 'cyan')
        Log.print("")

        Log.print("lf <targets>", 'bright_green')
        Log.print("  List broadcastable files on client(s)", 'white')
        Log.print("  Example: lf all", 'cyan')
        Log.print("")

        Log.print("start <targets> <file> [loop] [freq] [ps] [rt] [pi]", 'bright_green')
        Log.print("  Start broadcasting on client(s)", 'white')
        Log.print("  Example: start all broadcast.wav 100.5 MyRadio", 'cyan')
        Log.print("")

        Log.print("stop <targets>", 'bright_green')
        Log.print("  Stop broadcasting on client(s)", 'white')
        Log.print("  Example: stop all", 'cyan')
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

    if args.daemon and not args.ws:
        Log.error("Daemon mode requires a WebSocket port to be specified")
        sys.exit(1)

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
                    Log.server_message("Exiting...")
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
