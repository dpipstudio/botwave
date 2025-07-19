#!/opt/BotWave/venv/bin/python3
# this path HAS to be changed if you are not on a traditional linux distribution


# BotWave - Local Client
# A program by Douxx (douxx.tech | github.com/douxxtech)
# PiWave is required ! (https://github.com/douxxtech/piwave)
# Built on Top of Christophe Jacquet's amazing work: https://github.com/ChristopheJacquet/PiFmRds
# https://github.com/douxxtech/botwave
# https://botwave.dpip.lol
# A DPIP Studios project. https://dpip.lol
# Licensed under GPL-v3.0 (see LICENSE)

import os
import sys
import signal
import argparse
from typing import Optional
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

class BotWaveCLI:
    def __init__(self, upload_dir: str = "/opt/BotWave/uploads"):
        self.piwave = None
        self.running = False
        self.current_file = None
        self.broadcasting = False
        self.original_sigint_handler = None
        self.original_sigterm_handler = None
        self.command_history = []
        self.history_index = 0
        self.upload_dir = upload_dir
        os.makedirs(upload_dir, exist_ok=True)

    def _setup_signal_handlers(self):
        self.original_sigint_handler = signal.signal(signal.SIGINT, self._signal_handler)
        self.original_sigterm_handler = signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        Log.warning(f"Received signal {signum}, shutting down...")
        self.stop()
        sys.exit(0)

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
            self.piwave.play([file_path])
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

    def display_help(self):
        Log.header("BotWave Standalone CLI - Help")
        Log.section("Available Commands")
        Log.print("start <file> [frequency] [ps] [rt] [pi] [loop]", 'bright_green')
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
        Log.print("upload <source> <destination>", 'bright_green')
        Log.print("  Upload a file to the upload directory", 'white')
        Log.print("  Example: upload /path/to/myfile.wav broadcast.wav", 'cyan')
        Log.print("")
        Log.print("help", 'bright_green')
        Log.print("  Display this help message", 'white')
        Log.print("")
        Log.print("exit", 'bright_green')
        Log.print("  Exit the application", 'white')

    def upload_file(self, source_path: str, dest_name: str):
        if not os.path.exists(source_path):
            Log.error(f"Source file {source_path} not found")
            return False

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
    parser.add_argument('--skip-checks', action='store_true', help='Skip system requirements checks')
    args = parser.parse_args()

    Log.header("BotWave Local Client")

    check_requirements(args.skip_checks)

    cli = BotWaveCLI(args.upload_dir)
    cli._setup_signal_handlers()
    cli.running = True

    Log.info("Type 'help' for a list of available commands")

    while cli.running:
        try:
            cmd_input = input("\033[1;32mbotwave >\033[0m ").strip()
            if not cmd_input:
                continue

            cli.command_history.append(cmd_input)
            cli.history_index = len(cli.command_history)

            cmd_parts = cmd_input.split()
            command = cmd_parts[0].lower()

            if command == 'exit':
                cli.stop()
                break
            elif command == 'start':
                if len(cmd_parts) < 2:
                    Log.error("Usage: start <file> [frequency] [ps] [rt] [pi] [loop]")
                    continue

                file_path = os.path.join(args.upload_dir, cmd_parts[1])
                frequency = float(cmd_parts[2]) if len(cmd_parts) > 2 else 90.0
                ps = cmd_parts[3] if len(cmd_parts) > 3 else "RADIOOOO"
                rt = " ".join(cmd_parts[4:-2]) if len(cmd_parts) > 4 else "Broadcasting"
                pi = cmd_parts[-2] if len(cmd_parts) > 5 else "FFFF"
                loop = cmd_parts[-1].lower() == 'true' if len(cmd_parts) > 6 else False

                cli.start_broadcast(file_path, frequency, ps, rt, pi, loop)
            elif command == 'stop':
                cli.stop_broadcast()
            elif command == 'list':
                directory = cmd_parts[1] if len(cmd_parts) > 1 else None
                cli.list_files(directory)
            elif command == 'upload':
                if len(cmd_parts) < 3:
                    Log.error("Usage: upload <source> <destination>")
                    continue
                source = cmd_parts[1]
                destination = cmd_parts[2]
                cli.upload_file(source, destination)
            elif command == 'help':
                cli.display_help()
            else:
                Log.error(f"Unknown command: {command}")
                Log.info("Type 'help' for a list of available commands")
        except KeyboardInterrupt:
            Log.warning("Use 'exit' to exit")
        except EOFError:
            Log.info("Exiting...")
            cli.stop()
            break
        except Exception as e:
            Log.error(f"Error: {e}")

if __name__ == "__main__":
    main()
