#!/opt/BotWave/venv/bin/python3
# this path won't be correct if you didnt use the botwave.dpip.lol/install installer or similar.

# BotWave - Local Client
# A program by Douxx (douxx.tech | github.com/douxxtech)
# PiWave is required! (https://github.com/douxxtech/piwave)
# bw_custom is required! (https://github.com/dpipstudio/bw_custom)
# https://github.com/dpipstudio/botwave
# https://botwave.dpip.lol
# A DPIP Studio project. https://dpip.lol
# Licensed under GPL-v3.0 (see LICENSE)

import argparse
import os
import uuid
import signal
import subprocess
import shlex
import sys
import time
import urllib.request

# using this to access to the shared dir files
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from shared.alsa import Alsa
from shared.bw_custom import BWCustom
from shared.cat import check
from shared.converter import Converter, ConvertError, SUPPORTED_EXTENSIONS
from shared.handlers import HandlerExecutor
from shared.logger import Log, toggle_input
from shared.morser import text_to_morse
from shared.pw_monitor import PWM
from shared.queue import Queue
from shared.security import PathValidator, SecurityError
from shared.sstv import make_sstv_wav
from shared.syscheck import check_requirements
from shared.ws_cmd import WSCMDH

try:
    import readline
    HAS_READLINE = True
except:
    HAS_READLINE = False

try:
    from piwave import PiWave
    from piwave.backends import backend_classes
except ImportError:
    print("Error: PiWave module not found. Please install it first.")
    sys.exit(1)

class BotWaveCLI:
    def __init__(self, upload_dir: str = "/opt/BotWave/uploads", handlers_dir: str = "/opt/BotWave/handlers", ws_port: int = None, passkey: str = None, talk: bool = False):
        self.piwave = None
        self.running = False
        self.current_file = None
        self.broadcasting = False
        self.original_sigint_handler = None
        self.original_sigterm_handler = None
        self.upload_dir = upload_dir
        self.handlers_dir = handlers_dir
        self.handlers_executor = HandlerExecutor(handlers_dir, self._execute_command)
        self.silent = not talk # if silent = True, piwave wont output any logs
        self.piwave_monitor = PWM()
        self.alsa = Alsa()
        self.queue = Queue(client_instance=self, is_local=True, upload_dir=upload_dir)
        self.ws_port = ws_port
        self.ws_server = None
        self.ws_clients = set()
        self.ws_loop = None
        self.passkey = passkey
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

    def _start_websocket_server(self):
        self.ws_handler = WSCMDH(
            host="0.0.0.0",
            port=self.ws_port,
            passkey=self.passkey,
            command_executor=self._execute_command,
            is_server=False
        )
        self.ws_handler.start()

    def _execute_command(self, command: str):
        try:

            if "#" in command:
                command = command.split("#", 1)[0]

            command = command.strip()
            if not command:
                return True

            cmd_parts = shlex.split(command)
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
                ps = cmd_parts[4] if len(cmd_parts) > 4 else "BotWave"
                rt = " ".join(cmd_parts[5:-1]) if len(cmd_parts) > 5 else cmd_parts[1] # (file name)
                pi = cmd_parts[-1] if len(cmd_parts) > 6 else "FFFF"
                self.start_broadcast(file_path, frequency, ps, rt, pi, loop)
                self.onstart_handlers()
                return True
            
            if cmd == 'live':
                frequency = float(cmd_parts[1]) if len(cmd_parts) > 1 else 90.0
                ps = cmd_parts[2] if len(cmd_parts) > 2 else "BotWave"
                rt = " ".join(cmd_parts[3:-1]) if len(cmd_parts) > 3 else "Broadcasting"
                pi = cmd_parts[-1] if len(cmd_parts) > 4 else "FFFF"

                self.start_live(frequency, ps, rt, pi)
                self.onstart_handlers()
                return True


            elif cmd == 'stop':
                self.stop_broadcast()
                self.onstop_handlers()
                self.queue.manual_pause()
                Log.broadcast("Broadcast stopped")
                return True
            
            elif cmd == 'queue':
                self.queue.parse(' '.join(cmd_parts[1:]))
                return True
            
            elif cmd == 'sstv':
                if len(cmd_parts) < 2:
                    Log.error("Usage: sstv <image_path> [mode] [output_wav] [frequency] [loop] [ps] [rt] [pi]")
                    return True

                img_path = cmd_parts[1]
                mode = cmd_parts[2] if len(cmd_parts) > 2 else None
                output_wav = cmd_parts[3] if len(cmd_parts) > 3 else os.path.join(self.upload_dir, os.path.splitext(os.path.basename(img_path))[0] + ".wav")
                frequency = float(cmd_parts[4]) if len(cmd_parts) > 4 else 90.0
                loop = cmd_parts[5].lower() == 'true' if len(cmd_parts) > 5 else False
                ps = cmd_parts[6] if len(cmd_parts) > 6 else "BotWave"
                rt = cmd_parts[7] if len(cmd_parts) > 7 else output_wav
                pi = cmd_parts[8] if len(cmd_parts) > 8 else "FFFF"

                if not os.path.exists(img_path):
                    Log.error(f"Image file {img_path} not found")
                    return True

                Log.sstv(f"Generating SSTV WAV from {img_path} using mode {mode or 'auto'}...")
                success = make_sstv_wav(img_path, output_wav, mode)
                if success:
                    Log.sstv(f"Broadcasting {output_wav} on {frequency} MHz...")
                    self.start_broadcast(output_wav, frequency, ps, rt, pi, loop)
                return True
            
            elif cmd == 'morse':
                if len(cmd_parts) < 2:
                    Log.error("Usage: morse <text|file> [wpm] [frequency] [loop] [ps] [rt] [pi]")
                    return True

                text_source = cmd_parts[1]
    
                if os.path.exists(text_source) and os.path.isfile(text_source):
                    try:
                        with open(text_source, "r", encoding="utf-8") as f:
                            text = f.read()
                        Log.morse(f"Loaded Morse text from file: {text_source}")
                    except Exception as e:
                        Log.error(f"Failed to read text file: {e}")
                        return True
                else:
                    text = text_source
                
                wpm = int(cmd_parts[2]) if len(cmd_parts) > 2 else 20
                frequency = float(cmd_parts[3]) if len(cmd_parts) > 3 else 90.0
                loop = cmd_parts[4].lower() == 'true' if len(cmd_parts) > 4 else False
                ps = cmd_parts[5] if len(cmd_parts) > 5 else "BOTWAVE"
                rt = cmd_parts[6] if len(cmd_parts) > 6 else "MORSE"
                pi = cmd_parts[7] if len(cmd_parts) > 7 else "FFFF"
                
                output_wav = os.path.join(self.upload_dir, f"morse_{uuid.uuid4().hex[:8]}.wav")
                
                Log.morse(f"Generating Morse WAV ({wpm} WPM @ 700Hz)...")
                success = text_to_morse(text=text, filename=output_wav, wpm=wpm, frequency=700)
                
                if not success or not os.path.exists(output_wav):
                    Log.error("Failed to generate Morse WAV")
                    return True
                
                Log.morse(f"Broadcasting {output_wav}...")
                self.start_broadcast(output_wav, frequency, ps, rt, pi, loop)
                self.onstart_handlers()
                return True

            elif cmd == 'list':
                directory = cmd_parts[1] if len(cmd_parts) > 1 else None
                self.list_files(directory)
                return True

            elif cmd == 'rm':
                if len(cmd_parts) < 2:
                    Log.error("Usage: rm <filename|all>")
                    return True
                
                self.remove_file(cmd_parts[1])
                return True
            
            elif cmd == 'upload':
                if len(cmd_parts) < 2:
                    Log.error("Usage: upload <source>")
                    return True
                
                source = cmd_parts[1]
                self.upload_file(source)
                return True
            
            elif cmd == 'handlers':
                if len(cmd_parts) > 1:
                    filename = cmd_parts[1]
                    self.handlers_executor.list_handler_commands(filename)
                else:
                    self.handlers_executor.list_handlers()

                return True
            
            elif cmd == 'help':
                self.display_help()
                return True
            
            elif cmd == '<':
                if len(cmd_parts) < 2:
                    Log.error("Usage: < <shell command>")
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
            
            else:
                Log.error(f"Unknown command: {cmd}")
                return True
            
        except Exception as e:
            Log.error(f"Error executing command '{command}': {e}")
            return True

    def onready_handlers(self, dir_path: str = None):
        self.handlers_executor.run_handlers("l_onready", dir_path)

    def onstart_handlers(self, dir_path: str = None):
        self.handlers_executor.run_handlers("l_onstart", dir_path)

    def onstop_handlers(self, dir_path: str = None):
        self.handlers_executor.run_handlers("l_onstop", dir_path)

    def _execute_handler(self, file_path: str, silent: bool = False):
        try:
            if not silent:
                Log.handler(f"Running handler on {file_path}")
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()

                    if line:
                        if line[0] != "#":
                            if not silent:
                                Log.handler(f"Executing command: {line}")
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
                Log.info(f"STDERR (err {return_code}):")
                for line in process.stderr:
                    Log.print(line, end='')

                Log.error(f"Command failed with return code {return_code}")
        except Exception as e:
            Log.error(f"Error executing shell command: {e}")

    def upload_file(self, source_path: str):
        allowed_source_dirs = [
            '/tmp',
            '/home',
            '/opt/BotWave',
            self.upload_dir,
            os.path.expanduser('~')
        ]

        try:
            source_path = PathValidator.validate_read(source_path, allowed_source_dirs)
        except SecurityError as e:
            Log.error(f"Access denied: {e}")
            return False

        if not os.path.exists(source_path):
            Log.error(f"Source {source_path} not found")
            return False

        if os.path.isdir(source_path):
            return self._upload_folder_contents(source_path)

        try:
            filename = os.path.basename(source_path)
            ext = os.path.splitext(filename)[1].lower()

            if ext != ".wav":
                if ext.lstrip(".") not in SUPPORTED_EXTENSIONS:
                    Log.error(f"Unsupported file type: {ext}")
                    return False

                # convert to wav
                dest_name = PathValidator.sanitize_filename(os.path.splitext(filename)[0] + ".wav")
                dest_path = PathValidator.safe_join(self.upload_dir, dest_name)

                Converter.convert_wav(source_path, dest_path, not self.silent)
                Log.success(f"File converted and uploaded to {dest_path}")
                return True

            # already wav = just copy
            dest_name = PathValidator.sanitize_filename(filename)
            dest_path = PathValidator.safe_join(self.upload_dir, dest_name)

        except SecurityError as e:
            Log.error(f"Invalid destination: {e}")
            return False
        except ConvertError as e:
            Log.error(str(e))
            return False

        try:
            with open(source_path, 'rb') as src_file, open(dest_path, 'wb') as dest_file:
                dest_file.write(src_file.read())

            Log.success(f"File uploaded successfully to {dest_path}")
            return True

        except Exception as e:
            Log.error(f"Error uploading file: {e}")
            return False

        

    def _upload_folder_contents(self, folder_path: str):
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

        success = 0

        for idx, filename in enumerate(files, 1):
            source_path = os.path.join(folder_path, filename)
            name, ext = os.path.splitext(filename)
            ext = ext.lower()

            Log.file(f"[{idx}/{len(files)}] Processing {filename}...")

            try:
                if ext == ".wav":
                    dest_name = PathValidator.sanitize_filename(filename)
                    dest_path = PathValidator.safe_join(self.upload_dir, dest_name)

                    with open(source_path, 'rb') as src, open(dest_path, 'wb') as dst:
                        dst.write(src.read())

                    Log.success(f"  Uploaded {filename}")
                    success += 1

                elif ext.lstrip(".") in SUPPORTED_EXTENSIONS:
                    dest_name = PathValidator.sanitize_filename(name + ".wav")
                    dest_path = PathValidator.safe_join(self.upload_dir, dest_name)

                    Converter.convert_wav(source_path, dest_path)
                    Log.success(f"  Converted & uploaded {dest_name}")
                    success += 1

                else:
                    Log.warning(f"  Skipped unsupported file: {filename}")

            except (ConvertError, SecurityError, OSError) as e:
                Log.error(f"  {filename} - {e}")

        Log.file(f"Folder upload completed: {success}/{len(files)} files processed")
        return success > 0


    def download_file(self, url: str, dest_name: str):
        def _download_reporthook(block_num, block_size, total_size):
            if total_size > 0:
                Log.progress_bar(block_num * block_size, total_size, prefix='Downloading:', suffix='Complete', style='yellow', icon='FILE', auto_clear=False)

            if block_num * block_num >= total_size:
                Log.progress_bar(block_num * block_size, total_size, prefix='Downloaded!', suffix='Complete', style='yellow', icon='FILE')


        try:
            if not dest_name:
                url_path = urllib.parse.urlparse(url).path
                dest_name = os.path.basename(url_path)

            try:
                dest_name = PathValidator.sanitize_filename(dest_name)
            except SecurityError as e:
                Log.error(f"Invalid destination filename: {e}")
                return False

            if not dest_name.lower().endswith('.wav'):
                Log.error("Only WAV files are supported")
                return False
            
            try:
                dest_path = PathValidator.safe_join(self.upload_dir, dest_name)
            except SecurityError as e:
                Log.error(f"Invalid destination path: {e}")
                return False
            
            Log.file(f"Downloading file from {url}...")
            urllib.request.urlretrieve(url, dest_path, reporthook=_download_reporthook)

            Log.success(f"File {dest_name} downloaded successfully to {dest_path}")
            return True
        
        except Exception as e:
            Log.error(f"Download error: {str(e)}")
            return False

    def start_broadcast(self, file_path: str, frequency: float = 90.0, ps: str = "BotWave", rt: str = "Broadcasting", pi: str = "FFFF", loop: bool = False, trigger_manual: bool = True):
        def finished():
            Log.info("Playback finished, stopping broadcast...")
            self.stop_broadcast()
            self.onstop_handlers()
            self.queue.on_broadcast_ended()

        if not os.path.exists(file_path):
            Log.error(f"File {file_path} not found")
            return False
        
        if trigger_manual:
            self.queue.manual_pause()
        
        if self.broadcasting:
            self.stop_broadcast()

        try:
            self.piwave = PiWave(
                frequency=frequency,
                ps=ps,
                rt=rt,
                pi=pi,
                loop=loop,
                backend="bw_custom",
                debug=not self.silent,
                silent=self.silent
            )

            self.current_file = file_path
            self.broadcasting = True
            success = self.piwave.play(file_path)

            if not loop:
                self.piwave_monitor.start(self.piwave, finished)
            
            if success:
                Log.success(f"Started broadcasting {file_path} on {frequency}MHz")
            else:
                Log.warning(f"PiWave returned a non-true status ?")

            return True
        
        except Exception as e:
            Log.error(f"Error starting broadcast: {e}")
            self.broadcasting = False
            self.current_file = None
            self.piwave = None
            return False

    def start_live(self, frequency: float = 90.0, ps: str = "BotWave", rt: str = "Broadcasting", pi: str = "FFFF"):
        def finished():
            Log.info("Playback finished, stopping broadcast...")
            self.stop_broadcast()
            self.onstop_handlers()
    
        if not self.alsa.is_supported():
            Log.alsa("Live broadcast is not supported on this installation.")
            Log.alsa("Did you setup the ALSA loopback card correctly ?")
            return False
        
        self.queue.manual_pause()
        
        if self.broadcasting:
            self.stop_broadcast()

        try:
            self.piwave = PiWave(
                frequency=frequency,
                ps=ps,
                rt=rt,
                pi=pi,
                backend="bw_custom",
                debug=not self.silent,
                silent=self.silent
            )

            self.alsa.start()

            self.current_file = "live_playback"
            self.broadcasting = True
            
            success = self.piwave.play(self.alsa.audio_generator(), sample_rate=self.alsa.rate, channels=self.alsa.channels, chunk_size=self.alsa.period_size)
            
            self.piwave_monitor.start(self.piwave, finished)

            if success:
                Log.success(f"Live broadcast started on {frequency}MHz")
            else:
                Log.warning(f"PiWave returned a non-true status ?")

            Log.alsa("To play live, please set your output sound card (ALSA) to 'BotWave'.")
            Log.alsa(f"We're expecting {self.alsa.rate}kHz on {self.alsa.channels} channels.")
            return True
        
        except Exception as e:
            Log.error(f"Error starting broadcast: {e}")
            self.alsa.stop()
            self.broadcasting = False
            self.current_file = None
            self.piwave = None
            return False
        

    def stop_broadcast(self):
        if not self.broadcasting:
            Log.warning("No broadcast is currently running")
            return False
        
        self.piwave_monitor.stop()
        if self.piwave:
            try:
                self.piwave.cleanup()
            except Exception as e:
                Log.error(f"Error stopping broadcast: {e}")
            finally:
                self.piwave = None

        self.alsa.stop()

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

    def remove_file(self, filename):

        if not filename:
            Log.info("No filename provided.")
            return
        
        if filename.lower() == 'all':
            # Remove all WAV files
            try:
                removed_count = 0

                for f in os.listdir(self.upload_dir):
                    if f.lower().endswith('.wav'):
                        os.remove(os.path.join(self.upload_dir, f))
                        removed_count += 1

                Log.success(f"Removed {removed_count} WAV files from {self.upload_dir}")
            
            except Exception as e:
                Log.error(f"Error removing WAV files: {str(e)}")
            
        else:
            try:
                filename = PathValidator.sanitize_filename(filename)
                file_path = PathValidator.safe_join(self.upload_dir, filename)
            except SecurityError as e:
                Log.error(f"Invalid filename: {e}")
                return


            if not os.path.exists(file_path):
                Log.error(f"File {filename} not found")
                return
            
            try:
                os.remove(file_path)
                Log.success(f"Removed file {filename}")
            
            except Exception as e:
                Log.error(f"Error removing file {filename}: {str(e)}")


    def display_help(self):
        Log.header("BotWave Local Client - Help")
        Log.section("Available Commands")

        Log.print("start <file> [frequency] [loop] [ps] [rt] [pi]", "bright_green")
        Log.print("  Start broadcasting a WAV file", "white")
        Log.print("  Example:", "white")
        Log.print("    start broadcast.wav 100.5 true MyRadio \"My Radio Text\" FFFF", "cyan")
        Log.print("")

        Log.print("stop", "bright_green")
        Log.print("  Stop the current broadcast", "white")
        Log.print("  Example:", "white")
        Log.print("    stop", "cyan")
        Log.print("")

        Log.print("live [freq] [ps] [rt] [pi]", "bright_green")
        Log.print("  Start a live audio broadcast", "white")
        Log.print("  Example:", "white")
        Log.print("    live", "cyan")
        Log.print("")

        Log.print("queue [+|-|*|!|?]", "bright_green")
        Log.print("  Manage broadcast queue", "white")
        Log.print("  Use 'queue ?' for detailed help", "white")
        Log.print("")

        Log.print("sstv <image_path> [mode] [output_wav] [frequency] [loop] [ps] [rt] [pi]", "bright_green")
        Log.print("  Convert an image into a SSTV WAV file, and then broadcast it", "white")
        Log.print("  Example:", "white")
        Log.print("    sstv /path/to/mycat.png Robot36 cat.wav 90 false PsPs Cutie FFFF", "cyan")
        Log.print("")

        Log.print("morse <text|file> [wpm] [frequency] [loop] [ps] [rt] [pi]", "bright_green")
        Log.print("  Convert text to Morse code WAV and broadcast it", "white")
        Log.print("  Examples:", "white")
        Log.print("    morse \"CQ CQ DE BOTWAVE\" 18 90 false BOTWAVE MORSE", "cyan")
        Log.print("    morse message.txt", "cyan")
        Log.print("")

        Log.print("list [directory]", "bright_green")
        Log.print("  List files in the specified directory (default: upload directory)", "white")
        Log.print("  Example:", "white")
        Log.print("    list /opt/BotWave/uploads", "cyan")
        Log.print("")

        Log.print("rm <filename|all>", "bright_green")
        Log.print("  Remove a file", "white")
        Log.print("  Example:", "white")
        Log.print("    rm broadcast.wav", "cyan")
        Log.print("")

        Log.print("upload <targets> <file|folder>", "bright_green")
        Log.print("  Upload a file or folder to the upload directory", "white")
        Log.print("  Examples:", "white")
        Log.print("    upload broadcast.wav", "cyan")
        Log.print("    upload /home/bw/lib", "cyan")
        Log.print("")

        Log.print("dl <url> [destination]", "bright_green")
        Log.print("  Download a WAV file from a URL", "white")
        Log.print("  Example:", "white")
        Log.print("    download http://example.com/file.wav myfile.wav", "cyan")
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

        Log.print("help", "bright_green")
        Log.print("  Display this help message", "white")
        Log.print("  Example:", "white")
        Log.print("    help", "cyan")
        Log.print("")

        Log.print("exit", "bright_green")
        Log.print("  Exit the application", "white")
        Log.print("  Example:", "white")
        Log.print("    exit", "cyan")


    def stop(self):
        self.running = False
        if self.broadcasting:
            self.stop_broadcast()
        if self.original_sigint_handler:
            signal.signal(signal.SIGINT, self.original_sigint_handler)
        if self.original_sigterm_handler:
            signal.signal(signal.SIGTERM, self.original_sigterm_handler)

        Log.client("Client stopped")

def main():
    Log.header("BotWave Local Client")

    check() #from shared.cat

    parser = argparse.ArgumentParser(description='BotWave Standalone CLI Client')
    parser.add_argument('--upload-dir', default='/opt/BotWave/uploads', help='Directory to store uploaded files')
    parser.add_argument('--handlers-dir', default='/opt/BotWave/handlers', help='Directory to retrieve l_ handlers from')
    parser.add_argument('--skip-checks', action='store_true', help='Skip system requirements checks')
    parser.add_argument('--daemon', action='store_true', help='Run in daemon mode (non-interactive)')
    parser.add_argument('--ws', type=int, help='WebSocket port for remote control')
    parser.add_argument('--pk', help='Optional passkey for WebSocket authentication')
    parser.add_argument('--talk', action='store_true', help='Makes PiWave (broadcast manager) output logs visible.')

    args = parser.parse_args()

    check_requirements(args.skip_checks)

    cli = BotWaveCLI(args.upload_dir, args.handlers_dir, args.ws, args.pk, args.talk)
    cli._setup_signal_handlers()
    cli.running = True

    if args.ws:
        cli._start_websocket_server()

    Log.info("Type 'help' for a list of available commands")
    cli.onready_handlers(args.handlers_dir)

    if not args.daemon:
        if HAS_READLINE:
            readline.parse_and_bind('tab: complete')
            readline.parse_and_bind('set editing-mode emacs')
            readline.set_history_length(1000)
            try:
                readline.read_history_file("/opt/BotWave/.history")
            except FileNotFoundError:
                pass

        while cli.running:
            try:
                print()
                toggle_input(True)
                cmd_input = input("\033[1;32mbotwave ›\033[0m ").strip()
                toggle_input(False)

                if not cmd_input:
                    continue

                if HAS_READLINE:
                    readline.add_history(cmd_input)

                exit = cli._execute_command(cmd_input)

                if not exit:
                    break

            except KeyboardInterrupt:
                toggle_input(False)
                Log.warning("Use 'exit' to exit")

            except EOFError:
                toggle_input(False)
                Log.info("Exiting...")
                cli.stop()
                break

            except Exception as e:
                toggle_input(False)
                Log.error(f"Error: {e}")

        if HAS_READLINE:
            try:
                readline.write_history_file("/opt/BotWave/.history")
            except:
                pass
    else:
        Log.info("Running in daemon mode. Server will continue to run in the background.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            Log.warning()

if __name__ == "__main__":
    main()
