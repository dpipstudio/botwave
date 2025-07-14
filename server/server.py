#!/opt/BotWave_Deps/venv/bin/python3
# this path HAS to be changed if you are not on a traditional linux distribution

# BotWave - Server

# A program by Douxx (douxx.tech | github.com/douxxtech)
# https://github.com/douxxtech/botwave
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
from datetime import datetime
from typing import Dict, List, Optional

PROTOCOL_VERSION = "1.0.0" # if missmatch of 1th or 2th part: error
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
    }

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
        # dont interrupt startup for client updates, we do not care
        return None

def versions_compatible(server_version: str, client_version: str) -> bool:
    server_tuple = parse_version(server_version)
    client_tuple = parse_version(client_version)

    return server_tuple[:2] == client_tuple[:2]

class BotWaveClient:
    def __init__(self, conn: socket.socket, addr: tuple, machine_info: dict, 
                 protocol_version: str = None, passkey: str = None):
        self.conn = conn
        self.addr = addr
        self.machine_info = machine_info
        self.protocol_version = protocol_version or "unknown"
        self.connected_at = datetime.now()
        self.last_seen = datetime.now()
        self.passkey = passkey
        self.authenticated = False

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
    def __init__(self, host: str = '0.0.0.0', port: int = 9938, passkey: str = None):
        self.host = host
        self.port = port
        self.passkey = passkey
        self.clients: Dict[str, BotWaveClient] = {}
        self.server_socket = None
        self.running = False
        self.command_history = []
        self.history_index = 0

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
        except Exception as e:
            Log.error(f"Error starting server: {e}")
            sys.exit(1)

    def _check_updates_background(self):
        time.sleep(2)  # give server time to start
        Log.info("Checking for protocol updates...")
        try:
            latest_version = check_for_updates(PROTOCOL_VERSION, VERSION_CHECK_URL)
            if latest_version:
                Log.update_message(f"Update available! Latest version: {latest_version}")
                Log.update_message("Consider updating to the latest version for compatibility")
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

                # check auth
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
                    break
                time.sleep(30)
            except Exception as e:
                Log.error(f"Error maintaining connection with {client_id}: {e}")
                if client_id in self.clients:
                    del self.clients[client_id]
                break

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
                    # Send the file data
                    client.conn.sendall(file_data)

                    # Receive confirmation
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

    def start_broadcast(self, client_targets: str, filename: str, frequency: float = 90.0,
                       ps: str = "RADIOOOO", rt: str = "Broadcasting since 2025", pi: str = "FFFF",
                       loop: bool = False):
        target_clients = self._parse_client_targets(client_targets)
        if not target_clients:
            return False

        command = {
            "type": "start_broadcast",
            "filename": filename,
            "frequency": frequency,
            "ps": ps,
            "rt": rt,
            "pi": pi,
            "loop": loop
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

def display_help():
    Log.header("BotWave Socket Manager - Help")
    Log.section("Available Commands")
    Log.print("list", 'bright_green')
    Log.print("  List all connected clients", 'white')
    Log.print("")
    Log.print("upload <targets> <file>", 'bright_green')
    Log.print("  Upload a WAV file to client(s)", 'white')
    Log.print("  Example: upload all broadcast.wav", 'cyan')
    Log.print("")
    Log.print("start <targets> <file> [freq] [ps] [rt] [pi] [loop]", 'bright_green')
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
    parser = argparse.ArgumentParser(description='BotWave Socket Manager - Server')
    parser.add_argument('--host', default='0.0.0.0', help='Server host')
    parser.add_argument('--port', type=int, default=9938, help='Server port')
    parser.add_argument('--pk', help='Optional passkey for authentication')
    parser.add_argument('--skip-update-check', action='store_true',
                       help='Skip checking for protocol updates')
    args = parser.parse_args()
    
    Log.header("BotWave Socket Manager - Server")
    
    server = BotWaveServer(args.host, args.port, args.pk)
    server.start()
    
    Log.print("Type 'help' for a list of available commands", 'bright_yellow')
    try:
        while True:
            try:
                print()
                cmd_input = input("\033[1;32mbotwave>\033[0m ").strip()
                if not cmd_input:
                    continue
                server.command_history.append(cmd_input)
                server.history_index = len(server.command_history)
                cmd = cmd_input.split()
                command = cmd[0].lower()
                if command == 'exit':
                    server.kick_client("all", "The server is closing.")
                    break
                elif command == 'list':
                    server.list_clients()
                elif command == 'upload':
                    if len(cmd) < 3:
                        Log.error("Usage: upload <targets> <file>")
                        Log.info("Targets: 'all', client_id, hostname, or comma-separated list")
                        continue
                    server.upload_file(cmd[1], cmd[2])
                elif command == 'start':
                    if len(cmd) < 3:
                        Log.error("Usage: start <targets> <file> [freq] [ps] [rt] [pi] [loop]")
                        Log.info("Targets: 'all', client_id, hostname, or comma-separated list")
                        continue
                    frequency = float(cmd[3]) if len(cmd) > 3 else 90.0
                    ps = cmd[4] if len(cmd) > 4 else "BotWave"
                    rt = cmd[5] if len(cmd) > 5 else "Broadcasting"
                    pi = cmd[6] if len(cmd) > 6 else "FFFF"
                    loop = cmd[7].lower() == 'true' if len(cmd) > 7 else False
                    server.start_broadcast(cmd[1], cmd[2], frequency, ps, rt, pi, loop)
                elif command == 'stop':
                    if len(cmd) < 2:
                        Log.error("Usage: stop <targets>")
                        Log.info("Targets: 'all', client_id, hostname, or comma-separated list")
                        continue
                    server.stop_broadcast(cmd[1])
                elif command == 'kick':
                    if len(cmd) < 2:
                        Log.error("Usage: kick <targets> [reason]")
                        Log.info("Targets: 'all', client_id, hostname, or comma-separated list")
                        continue
                    reason = " ".join(cmd[2:]) if len(cmd) > 2 else "Kicked by administrator"
                    server.kick_client(cmd[1], reason)
                elif command == 'restart':
                    if len(cmd) < 2:
                        Log.error("Usage: restart <targets>")
                        Log.info("Targets: 'all', client_id, hostname, or comma-separated list")
                        continue
                    server.restart_client(cmd[1])
                elif command == 'help':
                    display_help()
                else:
                    Log.error(f"Unknown command: {command}")
                    Log.info("Type 'help' for a list of available commands")
            except KeyboardInterrupt:
                Log.warning("Use 'exit' to exit")
            except EOFError:
                Log.server_message("Exiting...")
                break
            except Exception as e:
                Log.error(f"Error: {e}")
    finally:
        server.stop()

if __name__ == "__main__":
    main()
