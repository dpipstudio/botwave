#!/opt/BotWave/venv/bin/python3
# this path won't be correct if you didnt use the botwave.dpip.lol/install installer or similar.


# BotWave - Client
# A program by Douxx (douxx.tech | github.com/douxxtech)
# PiWave is required ! (https://github.com/douxxtech/piwave)
# Built on Top of Christophe Jacquet's amazing work: https://github.com/ChristopheJacquet/PiFmRds
# https://github.com/dpipstudio/botwave
# https://botwave.dpip.lol
# A DPIP Studios project. https://dpip.lol
# Licensed under GPL-v3.0 (see LICENSE)


import argparse
from datetime import datetime, timezone
import getpass
import json
import os
import platform
import queue
import signal
import socket
import sys
import threading
import time
import urllib.request
from typing import Dict, Optional

# using this to access to the shared dir files
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from shared.bw_custom import BWCustom
from shared.logger import Log
from shared.syscheck import check_requirements
from shared.version import PROTOCOL_VERSION, check_for_updates

try:
    from piwave import PiWave
    from piwave.backends import backend_classes
except ImportError:
    Log.error("PiWave module not found. Please install it first.")
    sys.exit(1)


class BotWaveClient:
    def __init__(self, server_host: str, server_port: int, upload_dir: str = "/opt/BotWave/uploads", passkey: str = None):
        self.server_host = server_host
        self.server_port = server_port
        self.upload_dir = upload_dir
        self.socket = None
        self.piwave = None
        self.running = False
        self.current_file = None
        self.broadcasting = False
        self.uploading = False
        self.passkey = passkey
        # command queue for main thread processing -> PiWave doesn't support being in a subthread
        self.command_queue = queue.Queue()
        self.response_queue = queue.Queue()
        self.broadcast_params = None
        self.broadcast_requested = False
        self.stop_broadcast_requested = False
        self.original_sigint_handler = None
        self.original_sigterm_handler = None
        os.makedirs(upload_dir, exist_ok=True)

        # load custom piwave backend
        backend_classes["bw_custom"] = BWCustom

    def _setup_signal_handlers(self):
        self.original_sigint_handler = signal.signal(signal.SIGINT, self._signal_handler)
        self.original_sigterm_handler = signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        Log.warning(f"Received signal {signum}, shutting down...")
        self.stop()
        sys.exit(0)

    def connect(self):
        # connect to the server, if it's an external ip, make sure to open the firewall
        # if behind a NAT, make sure to do a port forwarding
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
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


            buffer = ""
            while '\n' not in buffer:
                data = self.socket.recv(1024).decode('utf-8')
                if not data:
                    raise Exception("Connection closed during registration")
                buffer += data
            
            # process only registration response
            first_line = buffer.split('\n', 1)[0].strip()
            reg_response = json.loads(first_line)


            if reg_response.get('type') == 'register_ok':
                Log.success(f"Successfully registered with server as {reg_response.get('client_id')}")
                server_version = reg_response.get('server_protocol_version', 'unknown')
                Log.version(f"Server protocol version: {server_version}")
                Log.version(f"Client protocol version: {PROTOCOL_VERSION}")
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

        if self.socket:
            try:
                self.socket.close()
            except:
                pass

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

                                if command.get('type') == 'ping' and not self.uploading:
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

                                if command.get('type') == 'send_file':
                                    try:
                                        # Handle file sending - this method manages its own responses
                                        self._handle_send_file(command)
                                    except Exception as e:
                                        Log.error(f"Send file error: {e}")
                                        error_response = {"status": "error", "message": f"Send error: {str(e)}"}
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
            self.stop()
            return {"status": "success", "message": "Client kicked"}
        
        elif cmd_type == 'restart':
            Log.info("Restart requested by server")
            self._stop_broadcast_main_thread()
            return {"status": "success", "message": "Restart acknowledged"}
        
        elif cmd_type == 'download_file':
            url = command.get('url')
            if not url:
                return {"status": "error", "message": "Missing URL"}
            return self._handle_download_file(url)
        
        elif cmd_type == 'list_files':
            return self._handle_list_files_request(command)
        
        elif cmd_type == 'remove_file':
            return self._handle_remove_file(command)
        
        else:
            return {"status": "error", "message": f"Unknown command type: {cmd_type}"}

    def _handle_upload_file(self, command: dict) -> dict:
        try:
            filename = command.get('filename')
            file_size = command.get('size')

            self.uploading = True

            if not filename or not file_size:
                return {"status": "error", "message": "Missing filename or size"}
            
            if not filename.endswith('.wav'):
                return {"status": "error", "message": "Only WAV files are supported"}
            
            original_timeout = self.socket.gettimeout()
            transfer_timeout = max(60, file_size / 100000)
            self.socket.settimeout(transfer_timeout)

            file_path = os.path.join(self.upload_dir, filename)

            Log.file(f"Preparing to receive file: {filename} ({file_size} bytes)")

            ready_response = {"status": "ready", "message": "Ready to receive file"}

            self.socket.sendall((json.dumps(ready_response) + '\n').encode('utf-8'))

            Log.file(f"Receiving file data...")
            received_data = b''
            
            # dynamic buffer sizing based on file size
            if file_size < 1024 * 1024:  # < 1MB
                chunk_size = 32768  # 32KB
            elif file_size < 10 * 1024 * 1024:  # < 10MB
                chunk_size = 131072  # 128KB
            elif file_size < 100 * 1024 * 1024:  # < 100MB
                chunk_size = 524288  # 512KB
            else:  # >= 100MB
                chunk_size = 1048576  # 1MB

            Log.file(f"Using chunk size: {chunk_size / 1024:.0f}KB")

            while len(received_data) < file_size:
                try:
                    remaining = file_size - len(received_data)
                    current_chunk_size = min(chunk_size, remaining)  # Don't read more than needed
                    
                    chunk = self.socket.recv(current_chunk_size)
                    if not chunk:
                        Log.error("Connection closed during file transfer")
                        break

                    received_data += chunk

                    if file_size > 1024 * 1024:  # files > 1MB
                        Log.progress_bar(len(received_data), file_size, prefix='Uploading:', suffix='Complete', style='yellow', icon='FILE', auto_clear=False)

                except socket.timeout:
                    Log.error("Timeout while receiving file data")
                    break

                except Exception as e:
                    Log.error(f"Error receiving file chunk: {e}")
                    break

            if file_size > 1024 * 1024:
                Log.progress_bar(file_size, file_size, prefix='Uploaded!', suffix='Complete', style='yellow', icon='FILE')
            if len(received_data) != file_size:
                Log.error(f"File upload incomplete: received {len(received_data)}/{file_size} bytes")
                self.socket.settimeout(original_timeout)
                return {"status": "error", "message": f"Incomplete file transfer"}
            
            # Write the file
            with open(file_path, 'wb') as f:
                f.write(received_data)

            Log.success(f"File {filename} uploaded successfully ({len(received_data)} bytes)")

            final_response = {"status": "uploaded", "message": "File uploaded successfully"}
            self.socket.sendall((json.dumps(final_response) + '\n').encode('utf-8'))
            self.socket.settimeout(original_timeout)

            self.uploading = False
            return final_response
        except Exception as e:
            Log.error(f"Upload error: {str(e)}")
            return {"status": "error", "message": f"Upload error: {str(e)}"}
        

    def _handle_send_file(self, command: dict):
        self.uploading = True
        
        try:
            filename = command.get('filename')
            
            if not filename:
                error_response = {"status": "error", "message": "Missing filename"}
                self.socket.send((json.dumps(error_response) + '\n').encode('utf-8'))
                self.uploading = False
                return
            
            file_path = os.path.join(self.upload_dir, filename)
            
            if not os.path.exists(file_path):
                error_response = {"status": "error", "message": f"File {filename} not found"}
                self.socket.send((json.dumps(error_response) + '\n').encode('utf-8'))
                self.uploading = False
                return
            
            file_size = os.path.getsize(file_path)
            
            Log.file(f"Preparing to send file: {filename} ({file_size} bytes)")
            
            # Send ready response
            ready_response = {"status": "ready", "size": file_size, "message": "Ready to send file"}
            self.socket.send((json.dumps(ready_response) + '\n').encode('utf-8'))
            
            # Dynamic chunk sizing based on file size
            if file_size < 1024 * 1024:  # < 1MB
                chunk_size = 32768  # 32KB
            elif file_size < 10 * 1024 * 1024:  # < 10MB
                chunk_size = 131072  # 128KB
            elif file_size < 100 * 1024 * 1024:  # < 100MB
                chunk_size = 524288  # 512KB
            else:  # >= 100MB
                chunk_size = 1048576  # 1MB
            
            Log.file(f"Sending file data... (chunk size: {chunk_size / 1024:.0f}KB)")
            
            # Send file data
            with open(file_path, 'rb') as f:
                bytes_sent = 0
                while bytes_sent < file_size:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    self.socket.sendall(chunk)
                    bytes_sent += len(chunk)
                    
                    if file_size > 1024 * 1024:  # Progress bar for files > 1MB
                        Log.progress_bar(bytes_sent, file_size, prefix=f'Sending {filename}:', suffix='Complete', style='yellow', icon='FILE', auto_clear=False)
            
            if file_size > 1024 * 1024:
                Log.progress_bar(file_size, file_size, prefix=f'Sent {filename}!', suffix='Complete', style='yellow', icon='FILE')
            
            # Wait for confirmation from server
            confirm_buffer = ""
            original_timeout = self.socket.gettimeout()
            self.socket.settimeout(10)
            
            while '\n' not in confirm_buffer:
                data = self.socket.recv(1024).decode('utf-8')
                if not data:
                    raise Exception("Connection closed while waiting for confirmation")
                confirm_buffer += data
            
            confirm_line = confirm_buffer.split('\n', 1)[0].strip()
            confirm_json = json.loads(confirm_line)
            
            if confirm_json.get('status') == 'received':
                Log.success(f"File {filename} sent successfully")
            else:
                Log.error(f"Server reported error: {confirm_json.get('message', 'Unknown error')}")
            
            self.socket.settimeout(original_timeout)
            self.uploading = False
            
        except Exception as e:
            Log.error(f"Send file error: {e}")
            self.uploading = False
            try:
                error_response = {"status": "error", "message": f"Send error: {str(e)}"}
                self.socket.send((json.dumps(error_response) + '\n').encode('utf-8'))
            except:
                pass
        
    def _handle_download_file(self, url: str) -> dict:
        def _download_reporthook(block_num, block_size, total_size):
            if total_size > 0:
                Log.progress_bar(block_num * block_size, total_size, prefix='Downloading:', suffix='Complete', style='yellow', icon='FILE', auto_clear=False)

            if block_num * block_num >= total_size:
                Log.progress_bar(block_num * block_size, total_size, prefix='Downloaded!', suffix='Complete', style='yellow', icon='FILE')



        try:
            filename = url.split('/')[-1]

            if not filename.lower().endswith('.wav'):
                return {"status": "error", "message": "Only WAV files are supported"}

            file_path = os.path.join(self.upload_dir, filename)

            Log.file(f"Downloading file from {url}...")
            urllib.request.urlretrieve(url, file_path, reporthook=_download_reporthook)

            Log.success(f"File {filename} downloaded successfully")
            return {"status": "success", "message": "File downloaded successfully"}
        except Exception as e:
            Log.error(f"Download error: {str(e)}")
            return {"status": "error", "message": f"Download error: {str(e)}"}
        

    def _handle_list_files_request(self, command: dict) -> dict:
        try:
            directory = self.upload_dir
            
            if not os.path.exists(directory): #should not be possible, but meh
                return {
                    "status": "error", 
                    "message": f"Upload directory {directory} does not exist"
                }
            
            wav_files = []
            
            try:
                for filename in os.listdir(directory):
                    if filename.lower().endswith('.wav'):
                        file_path = os.path.join(directory, filename)
                        
                        if os.path.isfile(file_path):
                            stat_info = os.stat(file_path)
                            
                            file_info = {
                                'name': filename,
                                'size': stat_info.st_size,
                                'modified': datetime.fromtimestamp(stat_info.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                            }
                            wav_files.append(file_info)
                
                # sort by name bcs why not
                wav_files.sort(key=lambda x: x['name'])
                
                Log.file(f"Listed {len(wav_files)} broadcastable WAV files")
                
                return {
                    "status": "success",
                    "message": f"Found {len(wav_files)} WAV files",
                    "files": wav_files,
                    "directory": directory
                }
                
            except PermissionError:
                return {
                    "status": "error",
                    "message": f"Permission denied accessing upload directory"
                }
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Error listing upload directory: {str(e)}"
                }
                
        except Exception as e:
            Log.error(f"List files error: {str(e)}")
            return {
                "status": "error",
                "message": f"List files error: {str(e)}"
            }
        
    def _handle_remove_file(self, command: dict) -> dict:
        filename = command.get('filename')

        if not filename:
            return {"status": "error", "message": "Missing filename"}
        
        if filename.lower() == 'all':
            # Remove all WAV files
            try:
                removed_count = 0

                for f in os.listdir(self.upload_dir):
                    if f.lower().endswith('.wav'):
                        os.remove(os.path.join(self.upload_dir, f))
                        removed_count += 1

                Log.success(f"Removed {removed_count} WAV files from {self.upload_dir}")

                return {"status": "success", "message": f"Removed {removed_count} WAV files"}
            
            except Exception as e:
                Log.error(f"Error removing WAV files: {str(e)}")
                return {"status": "error", "message": f"Error removing WAV files: {str(e)}"}
            
        else:

            file_path = os.path.join(self.upload_dir, filename)

            if not os.path.exists(file_path):
                return {"status": "error", "message": f"File {filename} not found"}
            
            try:
                os.remove(file_path)
                Log.success(f"Removed file {filename}")
                return {"status": "success", "message": f"Removed file {filename}"}
            
            except Exception as e:
                Log.error(f"Error removing file {filename}: {str(e)}")
                return {"status": "error", "message": f"Error removing file {filename}: {str(e)}"}



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
            # Get the timestamp start_at
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
                    Log.broadcast(f"Waiting {delay:.2f} seconds before starting broadcast...")
                    broadcast_thread = threading.Thread(target=self._start_broadcast_after_delay, args=(delay,))
                    broadcast_thread.daemon = True
                    broadcast_thread.start()
                    return {"status": "success", "message": f"Broadcast scheduled to start in {delay:.2f} seconds"}
                else:
                    self._start_broadcast_main_thread()
                    return {"status": "success", "message": "Broadcasting started"}
            else:
                self._start_broadcast_main_thread()
                return {"status": "success", "message": "Broadcasting started"}
        except Exception as e:
            Log.error(f"Broadcast error: {str(e)}")
            return {"status": "error", "message": f"Broadcast error: {str(e)}"}

    def _start_broadcast_after_delay(self, delay: float):
        try:
            time.sleep(delay)
            self.broadcast_requested = True
        except Exception as e:
            Log.error(f"Error starting broadcast after delay: {str(e)}")

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
                backend="bw_custom",
                debug=False
            )
            self.current_file = params['filename']
            self.broadcasting = True
            self.broadcast_requested = False
            self.piwave.play(params['file_path'])
            Log.broadcast(f"PiWave broadcast started for {params['filename']}")
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
            Log.broadcast("Stopping broadcast...")
            return {"status": "success", "message": "Stopping broadcast"}
        except Exception as e:
            Log.error(f"Stop error: {str(e)}")
            return {"status": "error", "message": f"Stop error: {str(e)}"}

    def _stop_broadcast_main_thread(self):
        if self.piwave:
            try:
                self.piwave.cleanup() # both stops AND cleanups
                Log.broadcast("PiWave stopped")
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

        Log.client("Client stopped")


def main():
    Log.header("BotWave - Client")

    parser = argparse.ArgumentParser(description='BotWave - Client')
    parser.add_argument('server_host', nargs='?', help='Server hostname or IP address')
    parser.add_argument('--port', type=int, default=9938, help='Server port')
    parser.add_argument('--upload-dir', default='/opt/BotWave/uploads',
                       help='Directory to store uploaded files')
    parser.add_argument('--skip-checks', action='store_true',
                       help='Skip system requirements checks')
    parser.add_argument('--pk', nargs='?', const='', default=None, 
                       help='Optional passkey for authentication')
    parser.add_argument('--skip-update-check', action='store_true',
                       help='Skip checking for protocol updates')
    args = parser.parse_args()

    if not args.server_host:
        args.server_host = input("Enter server hostname or IP address: ").strip()
        if not args.server_host:
            Log.error("Server hostname/IP is required")
            sys.exit(1)

    if args.pk == '':
        pk_input = getpass.getpass("Enter passkey: ").strip()
        args.pk = pk_input or None

    if not args.skip_checks:
        check_requirements()

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
