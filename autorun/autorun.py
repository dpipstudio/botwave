#!/opt/BotWave/venv/bin/python3
# this path won't be correct if you didnt use the botwave.dpip.lol/install installer or similar.


# BotWave - AutoRunner
# A program by Douxx (douxx.tech | github.com/douxxtech)
# PiWave is required ! (https://github.com/douxxtech/piwave)
# Built on Top of Christophe Jacquet's amazing work: https://github.com/ChristopheJacquet/PiFmRds
# https://github.com/douxxtech/botwave
# https://botwave.dpip.lol
# A DPIP Studios project. https://dpip.lol
# Licensed under GPL-v3.0 (see LICENSE)

import os
import sys
import subprocess
import argparse
import platform
import pwd
import grp
from pathlib import Path
from typing import List, Optional

# Configuration
BOTWAVE_BASE_DIR = "/opt/BotWave"
VENV_PYTHON = "/opt/BotWave/venv/bin/python3"
CLIENT_SCRIPT = "/opt/BotWave/client/client.py"
SERVER_SCRIPT = "/opt/BotWave/server/server.py"
LOCAL_SCRIPT = "/opt/BotWave/local/local.py"
SYSTEMD_DIR = "/etc/systemd/system"

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
        'service': 'SVC',
        'system': 'SYS',
        'file': 'FILE',
        'install': 'INST',
        'start': 'START',
        'stop': 'STOP',
        'status': 'STAT',
        'uninstall': 'UNINST',
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
    def service_message(cls, message: str):
        cls.print(message, 'magenta', 'service')

    @classmethod
    def system_message(cls, message: str):
        cls.print(message, 'cyan', 'system')

    @classmethod
    def file_message(cls, message: str):
        cls.print(message, 'yellow', 'file')

    @classmethod
    def install_message(cls, message: str):
        cls.print(message, 'bright_green', 'install')

    @classmethod
    def start_message(cls, message: str):
        cls.print(message, 'bright_green', 'start')

    @classmethod
    def stop_message(cls, message: str):
        cls.print(message, 'bright_red', 'stop')

    @classmethod
    def status_message(cls, message: str):
        cls.print(message, 'bright_cyan', 'status')

    @classmethod
    def uninstall_message(cls, message: str):
        cls.print(message, 'bright_yellow', 'uninstall')

class SystemdService:
    def __init__(self, service_name: str, script_path: str, args: List[str], run_as_root: bool = False, user: Optional[str] = None):
        self.service_name = service_name
        self.script_path = script_path
        self.args = args
        self.run_as_root = run_as_root
        self.user = user or (None if run_as_root else os.getenv('SUDO_USER', os.getenv('USER')))

    def generate_service_file(self):
        args_str = ' '.join(self.args) if self.args else ''
        service_content = f"""[Unit]
Description=BotWave {self.service_name.replace('bw-', '').title()}
After=network.target
Wants=network.target

[Service]
Type=simple
ExecStart={VENV_PYTHON} {self.script_path} {args_str}
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=botwave-{self.service_name.replace('bw-', '')}
"""
        if self.run_as_root:
            service_content += "User=root\nGroup=root\n"
        else:
            service_content += f"User={self.user}\n"
            try:
                user_info = pwd.getpwnam(self.user)
                group_info = grp.getgrgid(user_info.pw_gid)
                service_content += f"Group={group_info.gr_name}\n"
            except (KeyError, OSError):
                pass

        service_content += """
#environment
Environment=PYTHONPATH=/opt/BotWave
Environment=PATH=/opt/BotWave/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
# security (if not root)
"""
        if not self.run_as_root:
            service_content += """NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/BotWave/uploads /opt/BotWave/handlers
"""

        service_content += """
[Install]
WantedBy=multi-user.target
"""
        return service_content

    def get_service_path(self):
        """Get the full path to the service file"""
        return os.path.join(SYSTEMD_DIR, f"{self.service_name}.service")

    def install(self):
        try:
            service_file_path = self.get_service_path()
            service_content = self.generate_service_file()
            with open(service_file_path, 'w') as f:
                f.write(service_content)
            os.chmod(service_file_path, 0o644)
            subprocess.run(['systemctl', 'daemon-reload'], check=True)
            subprocess.run(['systemctl', 'enable', self.service_name], check=True)
            Log.install_message(f"Service {self.service_name} installed and enabled")
            return True
        except subprocess.CalledProcessError as e:
            Log.error(f"Error installing service {self.service_name}: {e}")
            return False
        except Exception as e:
            Log.error(f"Error creating service file for {self.service_name}: {e}")
            return False

    def uninstall(self):
        try:
            subprocess.run(['systemctl', 'stop', self.service_name],
                         stderr=subprocess.DEVNULL)
            subprocess.run(['systemctl', 'disable', self.service_name],
                         stderr=subprocess.DEVNULL)
            service_file_path = self.get_service_path()
            if os.path.exists(service_file_path):
                os.remove(service_file_path)
            subprocess.run(['systemctl', 'daemon-reload'], check=True)
            Log.uninstall_message(f"Service {self.service_name} uninstalled")
            return True
        except Exception as e:
            Log.error(f"Error uninstalling service {self.service_name}: {e}")
            return False

    def start(self):
        try:
            subprocess.run(['systemctl', 'start', self.service_name], check=True)
            Log.start_message(f"Service {self.service_name} started")
            return True
        except subprocess.CalledProcessError as e:
            Log.error(f"Error starting service {self.service_name}: {e}")
            return False

    def stop(self):
        try:
            subprocess.run(['systemctl', 'stop', self.service_name], check=True)
            Log.stop_message(f"Service {self.service_name} stopped")
            return True
        except subprocess.CalledProcessError as e:
            Log.error(f"Error stopping service {self.service_name}: {e}")
            return False

    def status(self):
        try:
            result = subprocess.run(['systemctl', 'is-active', self.service_name],
                                  capture_output=True, text=True)
            status = result.stdout.strip()
            Log.status_message(f"Service {self.service_name}: {status}")
            if status == 'active':
                subprocess.run(['journalctl', '-u', self.service_name, '--lines=10', '--no-pager'])
            return status == 'active'
        except subprocess.CalledProcessError:
            Log.status_message(f"Service {self.service_name}: not found")
            return False

def check_system_requirements():
    errors = []
    if platform.system() not in ['Linux', 'Darwin']:
        errors.append("This script requires a Unix-like system (Linux/macOS)")
    if not os.path.exists('/bin/systemctl') and not os.path.exists('/usr/bin/systemctl'):
        errors.append("systemd is required but not found")
    if os.geteuid() != 0:
        errors.append("This script must be run as root (use sudo)")
    if not os.path.exists(BOTWAVE_BASE_DIR):
        errors.append(f"BotWave directory not found: {BOTWAVE_BASE_DIR}")
    if not os.path.exists(VENV_PYTHON):
        errors.append(f"Python virtual environment not found: {VENV_PYTHON}")
    if errors:
        Log.error("System requirements check failed:")
        for error in errors:
            Log.error(f"  - {error}")
        return False
    Log.success("System requirements check passed")
    return True

def check_script_exists(script_path: str, script_type: str):
    if not os.path.exists(script_path):
        Log.error(f"{script_type} script not found: {script_path}")
        return False
    if not os.access(script_path, os.R_OK):
        Log.error(f"{script_type} script is not readable: {script_path}")
        return False
    Log.success(f"{script_type} script found: {script_path}")
    return True

def create_directories():
    directories = [
        "/opt/BotWave/uploads",
        "/opt/BotWave/handlers"
    ]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        Log.file_message(f"Directory ensured: {directory}")

def main():
    Log.header("BotWave Autorun - Systemd Service Manager")
    parser = argparse.ArgumentParser(
        description='BotWave Autorun - Systemd Service Manager',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  sudo bw-autorun client 192.168.1.100 --port 9938 --pk mypasskey
  sudo bw-autorun server --pk mypasskey
  sudo bw-autorun local --daemon
  sudo bw-autorun all 192.168.1.100 --port 9938
Service Management:
  sudo bw-autorun --start client
  sudo bw-autorun --stop server
  sudo bw-autorun --status all
  sudo bw-autorun --uninstall client
        """
    )
    parser.add_argument('mode', nargs='?', choices=['client', 'server', 'all', 'local'],
                       help='Service type to manage')
    parser.add_argument('args', nargs=argparse.REMAINDER, help='Arguments to pass to the service')
    parser.add_argument('--start', action='store_true', help='Start service(s)')
    parser.add_argument('--stop', action='store_true', help='Stop service(s)')
    parser.add_argument('--restart', action='store_true', help='Restart service(s)')
    parser.add_argument('--status', action='store_true', help='Show service status')
    parser.add_argument('--uninstall', action='store_true', help='Uninstall service(s)')

    args = parser.parse_args()

    if not check_system_requirements():
        sys.exit(1)

    create_directories()

    current_user = os.getenv('SUDO_USER', os.getenv('USER', 'root'))

    if args.start or args.stop or args.restart or args.status or args.uninstall:
        if not args.mode:
            Log.error("Mode (client/server/all/local) required for service management")
            sys.exit(1)

        services = []
        if args.mode in ['client', 'all']:
            services.append(SystemdService('bw-client', CLIENT_SCRIPT, [], True))
        if args.mode in ['server', 'all']:
            services.append(SystemdService('bw-server', SERVER_SCRIPT, [], False, current_user))
        if args.mode == 'local':
            services.append(SystemdService('bw-local', LOCAL_SCRIPT, ['--daemon'], False, current_user))

        for service in services:
            if args.start:
                service.start()
            elif args.stop:
                service.stop()
            elif args.restart:
                service.stop()
                service.start()
            elif args.status:
                service.status()
            elif args.uninstall:
                service.uninstall()
        sys.exit(0)

    if not args.mode:
        parser.print_help()
        sys.exit(1)

    success = True

    if args.mode in ['client', 'all']:
        if not check_script_exists(CLIENT_SCRIPT, 'Client'):
            success = False
        else:
            Log.info("Installing BotWave Client service...")
            client_service = SystemdService('bw-client', CLIENT_SCRIPT, args.args, True)
            if client_service.install():
                client_service.start()
            else:
                success = False

    if args.mode in ['server', 'all']:
        if not check_script_exists(SERVER_SCRIPT, 'Server'):
            success = False
        else:
            Log.info("Installing BotWave Server service...")
            server_args = args.args.copy()
            if '--daemon' not in server_args:
                server_args.append('--daemon')

            server_service = SystemdService('bw-server', SERVER_SCRIPT, server_args, False, current_user)
            if server_service.install():
                server_service.start()
            else:
                success = False

    if args.mode == 'local':
        if not check_script_exists(LOCAL_SCRIPT, 'Local'):
            success = False
        else:
            Log.info("Installing BotWave Local service...")
            local_args = args.args.copy()
            if '--daemon' not in local_args:
                local_args.append('--daemon')

            local_service = SystemdService('bw-local', LOCAL_SCRIPT, local_args, True, current_user)
            if local_service.install():
                local_service.start()
            else:
                success = False

    if success:
        Log.success(f"BotWave {args.mode} service(s) installed and started successfully!")
        Log.info("Service Management Commands:")
        Log.info("  sudo systemctl status bw-client    # Check client status")
        Log.info("  sudo systemctl status bw-server    # Check server status")
        if args.mode != 'local':
            Log.info("  sudo systemctl status bw-local     # Check local status")
        Log.info("  sudo systemctl stop bw-client      # Stop client")
        Log.info("  sudo systemctl start bw-client     # Start client")
        Log.info("  sudo journalctl -u bw-client -f    # View client logs")
        Log.info("  sudo journalctl -u bw-server -f    # View server logs")
        if args.mode != 'local':
            Log.info("  sudo journalctl -u bw-local -f     # View local logs")
    else:
        Log.error(f"Failed to install BotWave {args.mode} service(s)")
        sys.exit(1)

if __name__ == "__main__":
    main()
