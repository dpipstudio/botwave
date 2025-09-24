#!/opt/BotWave/venv/bin/python3
# this path won't be correct if you didnt use the botwave.dpip.lol/install installer or similar.

# BotWave - Local Client
# A program by Douxx (douxx.tech | github.com/douxxtech)
# PiWave is required! (https://github.com/douxxtech/piwave)
# Built on Top of Christophe Jacquet's amazing work: https://github.com/ChristopheJacquet/PiFmRds
# https://github.com/dpipstudio/botwave
# https://botwave.dpip.lol
# A DPIP Studios project. https://dpip.lol
# Licensed under GPL-v3.0 (see LICENSE)

import os
import sys
import signal
import argparse
from typing import Optional
import subprocess
import time
import urllib.request
import asyncio
import websockets
import json
import threading

try:
    from piwave import PiWave
except ImportError:
    print("Error: PiWave module not found. Please install it first.")
    sys.exit(1)

class Log:
    COLORS = {
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

class BotWaveCLI:
    def __init__(self, upload_dir: str = "/opt/BotWave/uploads", handlers_dir: str = "/opt/BotWave/handlers", ws_port: int = None, passkey: str = None):
        self.piwave = None
        self.running = False
        self.current_file = None
        self.broadcasting = False
        self.original_sigint_handler = None
        self.original_sigterm_handler = None
        self.command_history = []
        self.history_index = 0
        self.upload_dir = upload_dir
        self.handlers_dir = handlers_dir
        self.ws_port = ws_port
        self.ws_server = None
        self.ws_clients = set()
        self.ws_loop = None
        self.passkey = passkey
        os.makedirs(upload_dir, exist_ok=True)

    def _setup_signal_handlers(self):
        self.original_sigint_handler = signal.signal(signal.SIGINT, self._signal_handler)
        self.original_sigterm_handler = signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        Log.warning(f"Received signal {signum}, shutting down...")
        self.stop()
        sys.exit(0)

    def _start_websocket_server(self):
        async def handler(websocket):
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
                self.ws_clients.add(websocket)
                Log.set_ws_clients(self.ws_clients)

                async for message in websocket:
                    Log.client_message(f"WebSocket CMD: {message}")
                    def inject_cmd():
                        self.command_history.append(message)
                        self.history_index = len(self.command_history)
                        self._execute_command(message)
                    asyncio.get_event_loop().call_soon_threadsafe(inject_cmd)
            except asyncio.TimeoutError:
                await websocket.send(json.dumps({"type": "error", "message": "Authentication timeout"}))
                await websocket.close()
            finally:
                self.ws_clients.discard(websocket)
                Log.set_ws_clients(self.ws_clients)

        async def start_server():
            async with websockets.serve(handler, "0.0.0.0", self.ws_port):
                Log.server_message(f"WebSocket server started on 0.0.0.0:{self.ws_port}")
                await asyncio.Future()

        def run_server():
            self.ws_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.ws_loop)
            Log.ws_loop = self.ws_loop
            self.ws_loop.run_until_complete(start_server())

        threading.Thread(target=run_server, daemon=True).start()

    def _execute_command(self, command: str):
        try:
            cmd_parts = command.split()
            if not cmd_parts:
                return True
            cmd = cmd_parts[0].lower()
            if cmd == 'start':
                if len(cmd_parts) < 2:
                    Log.error("Usage: start <file> [frequency] [loop] [ps] [rt] [pi]")
                    return True
                file_path = os.path.join(self.upload_dir, cmd_parts[1])
                frequency = float(cmd_parts[2]) if len(cmd_parts) > 2 else 90.0
                loop = cmd_parts[3].lower() == 'true' if len(cmd_parts) > 3 else False
                ps = cmd_parts[4] if len(cmd_parts) > 4 else "RADIOOOO"
                rt = " ".join(cmd_parts[5:-1]) if len(cmd_parts) > 5 else "Broadcasting"
                pi = cmd_parts[-1] if len(cmd_parts) > 6 else "FFFF"
                self.start_broadcast(file_path, frequency, ps, rt, pi, loop)
                self.onstart_handlers()
                return True

            elif cmd == 'stop':
                self.stop_broadcast()
                self.onstop_handlers()
                return True
            elif cmd == 'list':
                directory = cmd_parts[1] if len(cmd_parts) > 1 else None
                self.list_files(directory)
                return True
            elif cmd == 'upload':
                if len(cmd_parts) < 3:
                    Log.error("Usage: upload <source> <destination>")
                    return True
                source = cmd_parts[1]
                destination = cmd_parts[2]
                self.upload_file(source, destination)
                return True
            elif cmd == 'handlers':
                if len(cmd_parts) > 1:
                    filename = cmd_parts[1]
                    self.list_handler_commands(filename)
                else:
                    self.list_handlers()
                return True
            elif cmd == 'help':
                self.display_help()
                return True
            elif cmd == '<':
                if len(cmd_parts) < 2:
                    Log.error("Usage: > <shell command>")
                    return True
                shell_command = ' '.join(cmd_parts[1:])
                self.run_shell_command(shell_command)
                return True
            elif cmd == 'dl':
                if len(cmd_parts) < 2:
                    Log.error("Usage: dl <url> [destination]")
                    return True
                url = cmd_parts[1]
                dest_name = cmd_parts[2] if len(cmd_parts) > 2 else None
                self.download_file(url, dest_name)
                return True
            elif cmd == 'exit':
                self.stop()
                return False
            elif cmd == '#':
                return True
            else:
                Log.error(f"Unknown command: {cmd}")
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
            if filename.endswith(".hdl") and filename.startswith("l_onready"):
                file_path = os.path.join(dir_path, filename)
                self._execute_handler(file_path, silent=False)
            elif filename.endswith(".shdl") and filename.startswith("l_onready"):
                file_path = os.path.join(dir_path, filename)
                self._execute_handler(file_path, silent=True)

    def onstart_handlers(self, dir_path: str = None):
        if dir_path is None:
            dir_path = self.handlers_dir
        if not os.path.exists(dir_path):
            Log.error(f"Directory {dir_path} not found")
            return False
        for filename in os.listdir(dir_path):
            if filename.endswith(".hdl") and filename.startswith("l_onstart"):
                file_path = os.path.join(dir_path, filename)
                self._execute_handler(file_path, silent=False)
            elif filename.endswith(".shdl") and filename.startswith("l_onstart"):
                file_path = os.path.join(dir_path, filename)
                self._execute_handler(file_path, silent=True)

    def onstop_handlers(self, dir_path: str = None):
        if dir_path is None:
            dir_path = self.handlers_dir
        if not os.path.exists(dir_path):
            Log.error(f"Directory {dir_path} not found")
            return False
        for filename in os.listdir(dir_path):
            if filename.endswith(".hdl") and filename.startswith("l_onstop"):
                file_path = os.path.join(dir_path, filename)
                self._execute_handler(file_path, silent=False)
            elif filename.endswith(".shdl") and filename.startswith("l_onstop"):
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

    def upload_file(self, source_path: str, dest_name: str):
        if not os.path.exists(source_path):
            Log.error(f"Source file {source_path} not found")
            return False

        if dest_name is None:
            dest_name = os.path.basename(source_path)
        dest_path = os.path.join(self.upload_dir, dest_name)
        try:
            with open(source_path, 'rb') as src_file:
                with open(dest_path, 'wb') as dest_file:
                    dest_file.write(src_file.read())
            Log.success(f"File uploaded successfully to {dest_path}")
            return True
        except Exception as e:
            Log.error(f"Error uploading file: {e}")
            return False

    def download_file(self, url: str, dest_name: str):
        try:
            if not dest_name:
                dest_name = url.split('/')[-1]
            if not dest_name.lower().endswith('.wav'):
                Log.error("Only WAV files are supported")
                return False
            dest_path = os.path.join(self.upload_dir, dest_name)
            Log.file_message(f"Downloading file from {url}...")
            urllib.request.urlretrieve(url, dest_path)
            Log.success(f"File {dest_name} downloaded successfully to {dest_path}")
            return True
        except Exception as e:
            Log.error(f"Download error: {str(e)}")
            return False

    def start_broadcast(self, file_path: str, frequency: float = 90.0, ps: str = "RADIOOOO", rt: str = "Broadcasting", pi: str = "FFFF", loop: bool = False):
        if not os.path.exists(file_path):
            Log.error(f"File {file_path} not found")
            return False
        if self.broadcasting:
            self.stop_broadcast()
        try:
            self.piwave = PiWave(
                frequency=frequency,
                ps=ps,
                rt=rt,
                pi=pi,
                loop=loop,
                debug=False
            )
            self.current_file = file_path
            self.broadcasting = True
            self.piwave.play(file_path)
            Log.success(f"Broadcast started for {file_path} on frequency {frequency} MHz")
            return True
        except Exception as e:
            Log.error(f"Error starting broadcast: {e}")
            self.broadcasting = False
            self.current_file = None
            self.piwave = None
            return False

    def stop_broadcast(self):
        if not self.broadcasting:
            Log.warning("No broadcast is currently running")
            return False
        if self.piwave:
            try:
                self.piwave.stop()
                Log.success("Broadcast stopped")
            except Exception as e:
                Log.error(f"Error stopping broadcast: {e}")
            finally:
                self.piwave = None
        self.broadcasting = False
        self.current_file = None
        return True

    def list_files(self, directory: str = None):
        target_dir = directory if directory else self.upload_dir
        try:
            files = [f for f in os.listdir(target_dir) if os.path.isfile(os.path.join(target_dir, f))]
            if not files:
                Log.info(f"No files found in the directory {target_dir}")
                return
            Log.info(f"Files in directory {target_dir}:")
            for file in files:
                Log.print(f"  {file}", 'white')
        except Exception as e:
            Log.error(f"Error listing files: {e}")

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

    def display_help(self):
        Log.header("BotWave Standalone CLI - Help")
        Log.section("Available Commands")
        Log.print("start <file> [frequency] [loop] [ps] [rt] [pi]", 'bright_green')
        Log.print("  Start broadcasting a WAV file", 'white')
        Log.print("  Example: start broadcast.wav 100.5 MyRadio \"My Radio Text\" FFFF true", 'cyan')
        Log.print("")
        Log.print("stop", 'bright_green')
        Log.print("  Stop the current broadcast", 'white')
        Log.print("")
        Log.print("list [directory]", 'bright_green')
        Log.print("  List files in the specified directory (default: upload directory)", 'white')
        Log.print("  Example: list /opt/BotWave/uploads", 'cyan')
        Log.print("")
        Log.print("upload <source> [destination]", 'bright_green')
        Log.print("  Upload a file to the upload directory", 'white')
        Log.print("  Example: upload /path/to/myfile.wav broadcast.wav", 'cyan')
        Log.print("")
        Log.print("dl <url> [destination]", 'bright_green')
        Log.print("  Download a WAV file from a URL", 'white')
        Log.print("  Example: download http://example.com/file.wav myfile.wav", 'cyan')
        Log.print("")
        Log.print("handlers [filename]", 'bright_green')
        Log.print("  List all handlers or commands in a specific handler file", 'white')
        Log.print("")
        Log.print("< <command>", 'bright_green')
        Log.print("  Run a shell command on the main OS", 'white')
        Log.print("  Example: < df -h", 'cyan')
        Log.print("")
        Log.print("help", 'bright_green')
        Log.print("  Display this help message", 'white')
        Log.print("")
        Log.print("exit", 'bright_green')
        Log.print("  Exit the application", 'white')

    def stop(self):
        self.running = False
        if self.broadcasting:
            self.stop_broadcast()
        if self.original_sigint_handler:
            signal.signal(signal.SIGINT, self.original_sigint_handler)
        if self.original_sigterm_handler:
            signal.signal(signal.SIGTERM, self.original_sigterm_handler)
        Log.info("Client stopped")

def _is_valid_executable(path: str) -> bool:
    return os.path.isfile(path) and os.access(path, os.X_OK)

def find_pi_fm_rds_path() -> Optional[str]:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    path_file = os.path.join(current_dir, "pi_fm_rds_path")
    if os.path.isfile(path_file):
        try:
            with open(path_file, "r") as file:
                path = file.read().strip()
                if _is_valid_executable(path):
                    return path
                else:
                    Log.error("[Launcher] The path in pi_fm_rds_path is invalid.")
                    Log.info("[Launcher] Please relaunch this program.")
                    Log.info("[Launcher] This won't happen every time.")
                    os.remove(path_file)
        except Exception as e:
            Log.error(f"Error reading {path_file}: {e}")
            os.remove(path_file)
    search_paths = ["/opt/BotWave", "/home", "/bin", "/usr/local/bin", "/usr/bin", "/sbin", "/usr/sbin", "/"]
    found = False
    for directory in search_paths:
        if not os.path.isdir(directory):
            continue
        try:
            for root, _, files in os.walk(directory):
                if "pi_fm_rds" in files:
                    path = os.path.join(root, "pi_fm_rds")
                    if _is_valid_executable(path):
                        with open(path_file, "w") as file:
                            file.write(path)
                        found = True
                        return path
        except Exception as e:
            pass
    if not found:
        Log.warning("Could not automatically find `pi_fm_rds`. Please enter the full path manually.")
        user_path = input("Enter the path to `pi_fm_rds`: ").strip()
        if _is_valid_executable(user_path):
            with open(path_file, "w") as file:
                file.write(user_path)
            return user_path
        Log.error("The path you provided is not valid or `pi_fm_rds` is not executable.")
        Log.info("Please make sure `pi_fm_rds` is installed and accessible, then restart the program.")
        exit(1)
    return None

def is_raspberry_pi() -> bool:
    try:
        with open('/proc/cpuinfo', 'r') as f:
            cpuinfo = f.read()
        return 'Raspberry' in cpuinfo
    except:
        return False

def check_requirements(skip_checks: bool = False):
    if skip_checks:
        return
    if not is_raspberry_pi():
        Log.warning("This doesn't appear to be a Raspberry Pi")
        response = input("Continue anyway? (y/N): ").lower()
        if response != 'y':
            sys.exit(1)
    if os.geteuid() != 0:
        Log.error("This client must be run as root for GPIO access")
        sys.exit(1)
    pi_fm_rds_path = find_pi_fm_rds_path()
    if not pi_fm_rds_path:
        Log.error("pi_fm_rds not found. Please install PiFmRds first.")
        sys.exit(1)
    else:
        Log.success(f"Found pi_fm_rds at: {pi_fm_rds_path}")

def main():
    parser = argparse.ArgumentParser(description='BotWave Standalone CLI Client')
    parser.add_argument('--upload-dir', default='/opt/BotWave/uploads', help='Directory to store uploaded files')
    parser.add_argument('--handlers-dir', default='/opt/BotWave/handlers', help='Directory to retrieve l_ handlers from')
    parser.add_argument('--skip-checks', action='store_true', help='Skip system requirements checks')
    parser.add_argument('--daemon', action='store_true', help='Run in daemon mode (non-interactive)')
    parser.add_argument('--ws', type=int, help='WebSocket port for remote control')
    parser.add_argument('--pk', help='Optional passkey for WebSocket authentication')
    args = parser.parse_args()

    Log.header("BotWave Local Client")
    check_requirements(args.skip_checks)

    cli = BotWaveCLI(args.upload_dir, args.handlers_dir, args.ws, args.pk)
    cli._setup_signal_handlers()
    cli.running = True

    if args.ws:
        cli._start_websocket_server()

    Log.info("Type 'help' for a list of available commands")
    cli.onready_handlers(args.handlers_dir)

    if not args.daemon:
        while cli.running:
            try:
                cmd_input = input("\033[1;32mbotwave ›\033[0m ").strip()
                if not cmd_input:
                    continue
                cli.command_history.append(cmd_input)
                cli.history_index = len(cli.command_history)
                exit = cli._execute_command(cmd_input)
                if not exit:
                    break
            except KeyboardInterrupt:
                Log.warning("Use 'exit' to exit")
            except EOFError:
                Log.info("Exiting...")
                cli.stop()
                break
            except Exception as e:
                Log.error(f"Error: {e}")
    else:
        Log.info("Running in daemon mode. Server will continue to run in the background.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            cli.stop()

if __name__ == "__main__":
    main()
