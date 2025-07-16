#!/opt/BotWave/venv/bin/python3
# this path HAS to be changed if you are not on a traditional linux distribution


# BotWave - Client

# A program by Douxx (douxx.tech | github.com/douxxtech)
# PiWave is required ! (https://github.com/douxxtech/piwave)
# Built on Top of Christophe Jacquet's amazing work: https://github.com/ChristopheJacquet/PiFmRds
# https://github.com/douxxtech/botwave
# https://botwave.dpip.lol
# A DPIP Studios project. https://dpip.lol
# Licensed under GPL-v3.0 (see LICENSE)



import socket
import json
import os
import sys
import argparse
import threading
import time
import platform
import queue
import signal
import urllib.request
import urllib.error
from typing import Optional, Dict
from datetime import datetime, timezone
try:
    from piwave import PiWave
except ImportError:
    print("Error: BotWave module not found. Please install it first.")
    sys.exit(1)

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
    """Parse version string into tuple of integers for comparison"""
    try:
        return tuple(map(int, version_str.split('.')))
    except (ValueError, AttributeError):
        return (0, 0, 0)

def check_for_updates(current_version: str, check_url: str) -> Optional[str]:
    """Check for protocol updates from remote URL"""
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

class BotWaveClient:
    def __init__(self, server_host: str, server_port: int, upload_dir: str = "/opt/BotWave/uploads", passkey: str = None):
        self.server_host = server_host
        self.server_port = server_port
        self.upload_dir = upload_dir
        self.socket = None
        self.BotWave = None
        self.running = False
        self.current_file = None
        self.broadcasting = False
        self.passkey = passkey
        # command queue for main thread processing -> fucking BotWave doesnt supports being in a subthread
        self.command_queue = queue.Queue()
        self.response_queue = queue.Queue()
        self.broadcast_params = None
        self.broadcast_requested = False
        self.stop_broadcast_requested = False
        self.original_sigint_handler = None
        self.original_sigterm_handler = None
        os.makedirs(upload_dir, exist_ok=True)

    def _setup_signal_handlers(self):
        self.original_sigint_handler = signal.signal(signal.SIGINT, self._signal_handler)
        self.original_sigterm_handler = signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        Log.warning(f"Received signal {signum}, shutting down...")
        self.stop()
        sys.exit(0)

    def connect(self):
        # connect to the server, if its an external ip, make sure to open the fw
        # if behind a NAT, make sure to do a port forwarding
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(30)
            Log.info(f"Attempting to connect to {self.server_host}:{self.server_port}...")
            self.socket.connect((self.server_host, self.server_port))

            # Send registration info with passkey and protocol version
            machine_info = {
                "hostname": platform.node(),
                "machine": platform.machine(),
                "system": platform.system(),
                "release": platform.release()
            }
            registration = {
                "type": "register",
                "protocol_version": PROTOCOL_VERSION,
                "machine_info": machine_info,
                "passkey": self.passkey
            }
            message = json.dumps(registration)
            self.socket.send((message + '\n').encode('utf-8'))

            response = self.socket.recv(1024).decode('utf-8').strip()
            reg_response = json.loads(response)

            if reg_response.get('type') == 'register_ok':
                Log.success(f"Successfully registered with server as {reg_response.get('client_id')}")
                server_version = reg_response.get('server_protocol_version', 'unknown')
                Log.version_message(f"Server protocol version: {server_version}")
                Log.version_message(f"Client protocol version: {PROTOCOL_VERSION}")
                return True
            elif reg_response.get('type') == 'auth_failed':
                Log.error("Authentication failed: Invalid passkey")
                return False
            elif reg_response.get('type') == 'version_mismatch':
                server_version = reg_response.get('server_version', 'unknown')
                client_version = reg_response.get('client_version', PROTOCOL_VERSION)
                Log.error(f"Protocol version mismatch!")
                Log.error(f"Server version: {server_version}")
                Log.error(f"Client version: {client_version}")
                Log.error("Please update your client or server to match protocol versions")
                return False
            else:
                Log.error("Registration failed")
                return False
        except Exception as e:
            Log.error(f"Error connecting to server: {e}")
            return False

    def start(self):
        if not self.connect():
            return False
        self.running = True
        self._setup_signal_handlers()
        threading.Thread(target=self._handle_network_commands, daemon=True).start()
        self._main_loop()
        return True

    def _main_loop(self): # a messy method to run all on main thread
        while self.running:
            try:
                if self.broadcast_requested and not self.broadcasting:
                    self._start_broadcast_main_thread()
                if self.stop_broadcast_requested and self.broadcasting:
                    self._stop_broadcast_main_thread()
                try:
                    command_data = self.command_queue.get_nowait()
                    command = command_data['command']
                    response = self._process_command(command)
                    self.response_queue.put({
                        'id': command_data['id'],
                        'response': response
                    })
                except queue.Empty:
                    pass
                time.sleep(0.1)
            except KeyboardInterrupt:
                break
            except Exception as e:
                Log.error(f"Error in main loop: {e}")
                time.sleep(1)

    def _handle_network_commands(self):
        buffer = ""
        command_id = 0
        while self.running:
            try:
                self.socket.settimeout(1.0)
                try:
                    data = self.socket.recv(4096)
                    if not data:
                        Log.warning("Server disconnected")
                        break

                    text_data = data.decode('utf-8')
                    buffer += text_data

                    while '\n' in buffer:
                        message, buffer = buffer.split('\n', 1)
                        if message.strip():
                            try:
                                command = json.loads(message.strip())

                                if command.get('type') == 'ping':
                                    response = {"type": "pong"}
                                    self.socket.send((json.dumps(response) + '\n').encode('utf-8'))
                                    continue

                                if command.get('type') == 'upload_file':
                                    try:
                                        # Handle file upload - this method manages its own responses
                                        self._handle_upload_file(command)
                                    except Exception as e:
                                        Log.error(f"File upload error: {e}")
                                        error_response = {"status": "error", "message": f"Upload error: {str(e)}"}
                                        self.socket.send((json.dumps(error_response) + '\n').encode('utf-8'))
                                    continue

                                # For other commands, use the queue system
                                command_id += 1
                                self.command_queue.put({
                                    'id': command_id,
                                    'command': command
                                })

                                timeout = 30
                                response = self._wait_for_response(command_id, timeout=timeout)
                                if response:
                                    self.socket.send((json.dumps(response) + '\n').encode('utf-8'))
                                else:
                                    error_response = {"status": "error", "message": "Command timeout"}
                                    self.socket.send((json.dumps(error_response) + '\n').encode('utf-8'))

                            except json.JSONDecodeError as e:
                                Log.error(f"Invalid JSON received: {message} - Error: {e}")
                            except Exception as e:
                                Log.error(f"Error processing message: {e}")

                except socket.timeout:
                    try:
                        self.response_queue.get_nowait()
                    except queue.Empty:
                        pass
                    continue

            except Exception as e:
                Log.error(f"Error handling network command: {e}")
                break

        self.running = False

    def _wait_for_response(self, command_id: int, timeout: int = 30) -> Optional[Dict]:
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response_data = self.response_queue.get_nowait()
                if response_data['id'] == command_id:
                    return response_data['response']
                else:
                    self.response_queue.put(response_data)
            except queue.Empty:
                pass
            time.sleep(0.1)
        return None

    def _process_command(self, command: dict) -> Optional[dict]:
        cmd_type = command.get('type')
        if cmd_type == 'start_broadcast':
            return self._handle_start_broadcast_request(command)
        elif cmd_type == 'stop_broadcast':
            return self._handle_stop_broadcast_request()
        elif cmd_type == 'kick':
            reason = command.get('reason', 'Kicked by administrator')
            Log.warning(f"Kicked from server: {reason}")
            self.running = False
            return {"status": "success", "message": "Client kicked"}
        elif cmd_type == 'restart':
            Log.info("Restart requested by server")
            self._stop_broadcast_main_thread()
            return {"status": "success", "message": "Restart acknowledged"}
        else:
            return {"status": "error", "message": f"Unknown command type: {cmd_type}"}

    def _handle_upload_file(self, command: dict) -> dict:
        try:
            filename = command.get('filename')
            file_size = command.get('size')
            if not filename or not file_size:
                return {"status": "error", "message": "Missing filename or size"}
            if not filename.endswith('.wav'):
                return {"status": "error", "message": "Only WAV files are supported"}

            file_path = os.path.join(self.upload_dir, filename)
            Log.file_message(f"Preparing to receive file: {filename} ({file_size} bytes)")

            ready_response = {"status": "ready", "message": "Ready to receive file"}
            self.socket.sendall((json.dumps(ready_response) + '\n').encode('utf-8'))

            Log.file_message(f"Receiving file data...")
            received_data = b''
            while len(received_data) < file_size:
                try:
                    remaining = file_size - len(received_data)
                    chunk_size = min(4096, remaining)
                    chunk = self.socket.recv(chunk_size)
                    if not chunk:
                        Log.error("Connection closed during file transfer")
                        break
                    received_data += chunk
                except socket.timeout:
                    Log.error("Timeout while receiving file data")
                    break
                except Exception as e:
                    Log.error(f"Error receiving file chunk: {e}")
                    break

            if len(received_data) != file_size:
                Log.error(f"File upload incomplete: received {len(received_data)}/{file_size} bytes")
                return {"status": "error", "message": f"Incomplete file transfer"}

            with open(file_path, 'wb') as f:
                f.write(received_data)

            Log.success(f"File {filename} uploaded successfully ({len(received_data)} bytes)")

            final_response = {"status": "uploaded", "message": "File uploaded successfully"}
            self.socket.sendall((json.dumps(final_response) + '\n').encode('utf-8'))
            return final_response

        except Exception as e:
            Log.error(f"Upload error: {str(e)}")
            return {"status": "error", "message": f"Upload error: {str(e)}"}

    def _handle_start_broadcast_request(self, command: dict) -> dict:
        try:
            filename = command.get('filename')
            if not filename:
                return {"status": "error", "message": "Missing filename"}

            file_path = os.path.join(self.upload_dir, filename)
            if not os.path.exists(file_path):
                return {"status": "error", "message": f"File {filename} not found"}

            if self.broadcasting:
                self.stop_broadcast_requested = True
                timeout = 0
                while self.broadcasting and timeout < 100:  # 10 secs timeout
                    time.sleep(0.1)
                    timeout += 1

            # Récupérer le timestamp start_at
            start_at = command.get('start_at', 0)

            self.broadcast_params = {
                'filename': filename,
                'file_path': file_path,
                'frequency': command.get('frequency', 90.0),
                'ps': command.get('ps', 'RADIOOOO'),
                'rt': command.get('rt', 'Broadcasting since 2025'),
                'pi': command.get('pi', 'FFFF'),
                'loop': command.get('loop', False)
            }

            if start_at > 0:
                current_time = datetime.now(timezone.utc).timestamp()
                if start_at > current_time:
                    delay = start_at - current_time
                    Log.broadcast_message(f"Waiting {delay:.2f} seconds before starting broadcast...")

                    broadcast_thread = threading.Thread(target=self._start_broadcast_after_delay, args=(delay,))
                    broadcast_thread.daemon = True
                    broadcast_thread.start()

                    return {"status": "success", "message": f"Broadcast scheduled to start in {delay:.2f} seconds"}
                else:
                    self._start_broadcast()
                    return {"status": "success", "message": "Broadcasting started"}
            else:
                self._start_broadcast()
                return {"status": "success", "message": "Broadcasting started"}

        except Exception as e:
            Log.error(f"Broadcast error: {str(e)}")
            return {"status": "error", "message": f"Broadcast error: {str(e)}"}

    def _start_broadcast_after_delay(self, delay: float):
        try:
            time.sleep(delay)
            self._start_broadcast()
        except Exception as e:
            Log.error(f"Error starting broadcast after delay: {str(e)}")

    def _start_broadcast(self):
        try:
            self.broadcast_requested = True
            Log.broadcast_message(
                f"Started broadcasting {self.broadcast_params['filename']} on {self.broadcast_params['frequency']} MHz"
            )
        except Exception as e:
            Log.error(f"Broadcast error: {str(e)}")

    def _start_broadcast_main_thread(self):
        if not self.broadcast_params:
            return
        try:
            params = self.broadcast_params
            self.piwave = PiWave(
                frequency=params['frequency'],
                ps=params['ps'],
                rt=params['rt'],
                pi=params['pi'],
                loop=params['loop'],
                debug=False
            )
            self.current_file = params['filename']
            self.broadcasting = True
            self.broadcast_requested = False
            self.piwave.send([params['file_path']])
            Log.broadcast_message(f"PiWave broadcast started for {params['filename']}")

        except Exception as e:
            Log.error(f"Error starting broadcast: {e}")
            self.broadcasting = False
            self.current_file = None
            self.piwave = None

    def _handle_stop_broadcast_request(self) -> dict:
        try:
            if not self.broadcasting:
                return {"status": "error", "message": "No broadcast running"}

            self.stop_broadcast_requested = True
            Log.broadcast_message("Broadcasting stopped")
            return {"status": "success", "message": "Broadcasting stopped"}

        except Exception as e:
            Log.error(f"Stop error: {str(e)}")
            return {"status": "error", "message": f"Stop error: {str(e)}"}

    def _stop_broadcast_main_thread(self):
        """Stop broadcast in main thread"""
        if self.piwave:
            try:
                self.piwave.stop()
                Log.broadcast_message("PiWave stopped")
            except Exception as e:
                Log.error(f"Error stopping PiWave: {e}")
            finally:
                self.piwave = None

        self.broadcasting = False
        self.current_file = None
        self.stop_broadcast_requested = False

    def stop(self):
        self.running = False
        if self.broadcasting:
            self._stop_broadcast_main_thread()
        if self.original_sigint_handler:
            signal.signal(signal.SIGINT, self.original_sigint_handler)
        if self.original_sigterm_handler:
            signal.signal(signal.SIGTERM, self.original_sigterm_handler)
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        Log.server_message("Client stopped")

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
                    Log.info("[Launcher] This won't happen everytime.")
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

def check_requirements(): # checking if its running on a raspberry pi, if we are root, and if we have pifmrds
    if not is_raspberry_pi():
        Log.warning("This doesn't appear to be a Raspberry Pi")
        response = input("Continue anyway? (y/N): ").lower()
        if response != 'y':
            sys.exit(1)
    # Check if running as root
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
    Log.header("BotWave - Client")
    
    Log.info("Checking for protocol updates...")
    try:
        latest_version = check_for_updates(PROTOCOL_VERSION, VERSION_CHECK_URL)
        if latest_version:
            Log.update_message(f"Update available! Latest version: {latest_version}")
            Log.update_message("Consider updating to the latest version by running 'sudo bw-update' in your shell.")
        else:
            Log.success("You are using the latest protocol version")
    except Exception as e:
        Log.warning("Unable to check for updates (continuing anyway)")
    
    parser = argparse.ArgumentParser(description='BotWave - Client')
    parser.add_argument('server_host', help='Server hostname or IP address')
    parser.add_argument('--port', type=int, default=9938, help='Server port')
    parser.add_argument('--upload-dir', default='/opt/BotWave/uploads',
                       help='Directory to store uploaded files')
    parser.add_argument('--skip-checks', action='store_true',
                       help='Skip system requirements checks')
    parser.add_argument('--pk', help='Optional passkey for authentication')
    parser.add_argument('--skip-update-check', action='store_true',
                       help='Skip checking for protocol updates')
    args = parser.parse_args()
    
    if not args.skip_checks:
        check_requirements()
    
    client = BotWaveClient(args.server_host, args.port, args.upload_dir, args.pk)
    Log.info(f"Starting BotWave client, connecting to {args.server_host}:{args.port}")
    Log.info(f"Upload directory: {args.upload_dir}")
    Log.info("Press Ctrl+C to stop")
    
    try:
        client.start()
    except KeyboardInterrupt:
        Log.warning("\nShutting down...")
        client.stop()

if __name__ == "__main__":
    main()