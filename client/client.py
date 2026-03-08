#!/opt/BotWave/venv/bin/python3
# this path won't be correct if you didnt use the botwave.dpip.lol/install installer or similar.

# BotWave - Client
# A program by Douxx (douxx.tech | github.com/douxxtech)
# PiWave is required ! (https://github.com/douxxtech/piwave)
# bw_custom is required! (https://github.com/dpipstudio/bw_custom)
# https://github.com/dpipstudio/botwave
# https://botwave.dpip.lol
# A DPIP Studio project. https://dpip.lol
# Licensed under GPL-v3.0 (see LICENSE)


import argparse
import asyncio
from datetime import datetime, timezone
import json
import os
import platform
import queue
import ssl
import sys
import tempfile
import urllib.request

# using this to access to the shared dir files
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from shared.alsa import Alsa
from shared.bw_custom import BWCustom
from shared.cat import check
from shared.converter import Converter, SUPPORTED_EXTENSIONS
from shared.env import Env
from shared.http import BWHTTPFileClient
from shared.logger import Log
from shared.protocol import ProtocolParser, Commands, PROTOCOL_VERSION
from shared.protomanager import ProtoManager
from shared.pw_monitor import PWM
from shared.security import PathValidator, SecurityError
from shared.socket import BWWebSocketClient
from shared.syscheck import check_requirements
from shared.tips import TipEngine
from shared.version import check_for_updates


try:
    from piwave import PiWave
    from piwave.backends import backend_classes
except ImportError:
    Log.error("PiWave module not found. Please install it first.")
    sys.exit(1)


class BotWaveClient:
    def __init__(self):
        # communications
        self.ws_client = None
        self.http_client = None
        self.proto = None

        # broadcast
        self.piwave = None
        self.piwave_monitor = PWM()
        self.broadcasting = False
        self.current_file = None
        self.broadcast_lock = asyncio.Lock() # using asyncio instead of thereading now
        self.alsa = Alsa()
        self.stream_task = None
        self.stream_active = False

        # states
        self.running = False
        self.registered = False
        self.client_id = None

        # utilities
        self.tips = TipEngine(is_server=False)

        backend_classes["bw_custom"] = BWCustom

    @property
    def server_host(self):
        return Env.get("SERVER_HOST")

    @property
    def http_host(self):
        return Env.get("FHOST")

    @property
    def ws_port(self):
        return Env.get_int("SERVER_PORT")

    @property
    def http_port(self):
        return Env.get_int("FPORT")

    @property
    def upload_dir(self):
        return Env.get("UPLOAD_DIR", "/opt/BotWave/uploads/")

    @property
    def passkey(self):
        return Env.get("PASSKEY")

    @property
    def talk(self):
        return Env.get_bool("TALK", False)

    @property
    def silent(self):
        return not self.talk

    def _create_ssl_context(self):
        # Creates SSL context accepting self-signed certificates
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        return ssl_context

    async def connect(self) -> bool:
        Log.client(f"Connecting to wss://{self.server_host}:{self.ws_port}...")

        if not await self.ws_client.connect():
            return False

        Log.success("WebSocket connected, registering...")

        # send register cmd
        machine_info = {
            "hostname": platform.node(),
            "machine": platform.machine(),
            "system": platform.system(),
            "release": platform.release()
        }

        await self.proto.fire(
            Commands.REGISTER,
            hostname=machine_info['hostname'],
            machine=machine_info['machine'],
            system=machine_info['system'],
            release=machine_info['release']
        )

        # if passkey, sending auth cmd
        if self.passkey:
            await self.proto.fire(Commands.AUTH, self.passkey)

        await self.proto.fire(Commands.VER, PROTOCOL_VERSION)

        for _ in range(50):  # wait up to 5s
            if self.registered:
                return True
            await asyncio.sleep(0.1)

        Log.error("Registration timeout")
        return False

    async def start(self):
        try:
            ssl_context = self._create_ssl_context()

            self.ws_client = BWWebSocketClient(
                ssl_context=ssl_context,
                on_message_callback=self._handle_server_msg
            )

            self.http_client = BWHTTPFileClient(ssl_context=ssl_context)

            self.proto = ProtoManager(send_fn=self.ws_client.send)

            if not await self.connect():
                await self.stop()

            self.running = True

            self.tips.start()

            # wait for disconnect (keeps client alive)
            await self.ws_client.wait_for_disconnect()

        except KeyboardInterrupt:
            Log.warning("Shutting down...")
        finally:
            await self.stop()

        return True

    async def _handle_server_msg(self, message: str):
        try:
            parsed = ProtocolParser.parse_command(message)
            command = parsed['command']
            kwargs = parsed['kwargs']

            #Log.info(f"Received: {command}")

            # registrations
            if command == Commands.REGISTER_OK:
                self.client_id = kwargs.get('client_id', 'unknown')
                self.registered = True
                Log.success(f"Registered as: {self.client_id}")
                return

            if command == Commands.AUTH_FAILED:
                Log.error("Authentication failed: Invalid passkey")
                await self.stop()
                return

            if command == Commands.VERSION_MISMATCH:
                server_ver = kwargs.get('server_version', 'unknown')
                Log.error(f"Protocol version mismatch! Server: {server_ver}, Client: {PROTOCOL_VERSION}")
                await self.stop()
                return

            # ping pong
            if command == Commands.PING:
                await self.proto.fire(Commands.PONG)
                return

            # broadcast
            if command == Commands.START:
                await self._handle_start_broadcast(parsed)
                return

            if command == Commands.STREAM_TOKEN:
                await self._handle_stream_token(parsed)
                return

            if command == Commands.STOP:
                await self._handle_stop_broadcast(parsed)
                return

            # files
            if command == Commands.UPLOAD_TOKEN:
                await self._handle_upload_token(parsed)
                return

            if command == Commands.DOWNLOAD_TOKEN:
                await self._handle_download_token(parsed)
                return

            if command == Commands.DOWNLOAD_URL:
                await self._handle_download_url(parsed)
                return

            # files management
            if command == Commands.LIST_FILES:
                await self._handle_list_files(parsed)
                return

            if command == Commands.REMOVE_FILE:
                await self._handle_remove_file(parsed)
                return

            # client management
            if command == Commands.KICK:
                reason = kwargs.get('reason', 'Kicked by administrator')
                Log.warning(f"Kicked: {reason}")
                await self.stop()
                return

            Log.warning(f"Unknown command: {command}")
            await self.proto.reply(parsed, Commands.ERROR, message=f"Unknown command: {command}. Perhaps a protocol mismatch ?")

        except Exception as e:
            Log.error(f"Error handling message: {e}")

    async def _handle_upload_token(self, parsed: dict):
        kwargs = parsed["kwargs"]

        token = kwargs.get('token')
        filename = kwargs.get('filename')
        size = int(kwargs.get('size', 0))

        if not token or not filename:
            await self.proto.reply(parsed, Commands.ERROR, message="Missing token or filename")
            return

        Log.file(f"Received upload token for: {filename} ({size if size > 0 else '?'} bytes)")

        try:
            filename = PathValidator.sanitize_filename(filename)
            filepath = PathValidator.safe_join(self.upload_dir, filename)

        except SecurityError as e:
            Log.error(f"Invalid filename from server: {e}")
            await self.proto.reply(parsed, Commands.ERROR, message="Provided filename raised a security violation")
            return

        def progress(bytes_sent, total):
            if total > 0:
                Log.progress_bar(bytes_sent, total, prefix=f'Uploading {filename}:', suffix='Complete', style='yellow', icon='FILE', auto_clear=(bytes_sent == total))

        success = await self.http_client.upload_file(
            server_host=self.http_host,
            server_port=self.http_port,
            token=token,
            filepath=filepath,
            progress_callback=progress
        )

        if success:
            Log.success(f"Upload completed: {filename}")
            await self.proto.reply(parsed, Commands.OK, message=f"Uploaded {filename}")

        else:
            Log.error(f"Upload failed: {filename}")
            await self.proto.reply(parsed, Commands.ERROR, message="Upload failed")


    async def _handle_download_token(self, parsed: dict):
        kwargs = parsed["kwargs"]

        token = kwargs.get('token')
        filename = kwargs.get('filename')

        if not token or not filename:
            await self.proto.reply(parsed, Commands.ERROR, message="Missing token or filename")
            return

        Log.file(f"Received download token for: {filename}")

        try:
            filename = PathValidator.sanitize_filename(filename)
            save_path = PathValidator.safe_join(self.upload_dir, filename)

        except SecurityError as e:
            Log.error(f"Invalid filename from server: {e}")
            await self.proto.reply(parsed, Commands.ERROR, message="Provided filename raised a security violation")
            return

        def progress(bytes_received, total):
            if total > 1024 * 1024:
                Log.progress_bar(bytes_received, total, prefix=f'Downloading {filename}:', suffix='Complete', style='yellow', icon='FILE', auto_clear=False)

            if bytes_received == total:
                Log.progress_bar(bytes_received, total, prefix=f'Downloaded {filename} !', suffix='Complete', style='yellow', icon='FILE', auto_clear=True)

        success = await self.http_client.download_file(
            server_host=self.http_host,
            server_port=self.http_port,
            token=token,
            save_path=save_path,
            progress_callback=progress
        )


        if success:
            Log.success(f"Download completed: {filename}")
            self.proto.reply(parsed, Commands.OK, message=f"Downloaded {filename}")

        else:
            Log.error(f"Download failed: {filename}")
            self.proto.reply(parsed, Commands.ERROR, message="Download failed")


    async def _handle_download_url(self, parsed: dict):
        kwargs = parsed["kwargs"]

        url = kwargs.get('url')
        filename = kwargs.get('filename')

        if not url or not filename:
            await self.proto.reply(parsed, Commands.ERROR, message="Missing URL or filename")
            return

        try:
            filename = PathValidator.sanitize_filename(filename)
            filepath = PathValidator.safe_join(self.upload_dir, filename)

        except SecurityError as e:
            Log.error(f"Invalid filename from server: {e}")
            await self.proto.reply(parsed, Commands.ERROR, message="Provided filename raised a security violation")
            return

        ext = os.path.splitext(filename)[1].lower().lstrip(".")
        converted = False

        try:
            Log.file(f"Downloading from URL: {url}")

            def download_with_progress(dest_path):
                headers = {
                    "User-Agent": Env.get("DOWNLOAD_UA", f"BotWaveDownloads/{PROTOCOL_VERSION} (+https://github.com/dpipstudio/botwave/)")
                }

                request = urllib.request.Request(url, headers=headers)

                with urllib.request.urlopen(request) as response, open(dest_path, "wb") as out_file:
                    out_file.write(response.read())

            loop = asyncio.get_event_loop()

            if ext == "wav":
                await loop.run_in_executor(None, download_with_progress, filepath)

            elif ext in SUPPORTED_EXTENSIONS:
                filepath = os.path.splitext(filepath)[0] + ".wav"
                filename = os.path.splitext(filename)[0] + ".wav"

                with tempfile.NamedTemporaryFile(delete=False, suffix="." + ext) as tmp:
                    tmp_path = tmp.name

                try:
                    await loop.run_in_executor(None, download_with_progress, tmp_path)
                    Converter.convert_wav(tmp_path, filepath, not self.silent)
                finally:
                    converted = True
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)

            else:
                raise ValueError(f"Unsupported file type from URL: .{ext}")

            if os.path.exists(filepath):
                file_size = os.path.getsize(filepath)
                Log.success(f"Downloaded: {filename} ({file_size if file_size > 0 else '?'} bytes{', converted' if converted else ''})")
                await self.proto.reply(parsed, Commands.OK, message=f"Downloaded {filename}{' (converted)' if converted else ''}")

            else:
                Log.error("Download failed: file not created")
                await self.proto.reply(parsed, Commands.ERROR, message="File not created")

        except urllib.error.URLError as e:
            Log.error(f"Network error: {e}")
            await self.proto.reply(parsed, Commands.ERROR, message=f"Network error: {str(e)}")

        except Exception as e:
            Log.error(f"Download failed: {e}")
            await self.proto.reply(parsed, Commands.ERROR, message=f"Error: {str(e)}")

    async def _handle_start_broadcast(self, parsed: dict):
        kwargs = parsed["kwargs"]
        filename = kwargs.get('filename')

        if not filename:
            await self.proto.reply(parsed, Commands.ERROR, message="Missing filename")
            return

        try:
            filename = PathValidator.sanitize_filename(filename)
            file_path = PathValidator.safe_join(self.upload_dir, filename)

        except SecurityError as e:
            Log.error(f"Invalid filename from server: {e}")
            await self.proto.reply(parsed, Commands.ERROR, message="Provided filename raised a security violation")
            return

        if not os.path.exists(file_path):
            await self.proto.reply(parsed, Commands.END, message=f"File not found: {filename}")
            return

        frequency = float(kwargs.get('freq', 90.0))
        ps = kwargs.get('ps', 'BotWave')
        rt = kwargs.get('rt', 'Broadcasting')
        pi = kwargs.get('pi', 'FFFF')
        loop = kwargs.get('loop', 'false').lower() == 'true'
        start_at = float(kwargs.get('start_at', 0))

        if start_at > 0:
            current_time = datetime.now(timezone.utc).timestamp()
            if start_at > current_time:
                delay = start_at - current_time
                Log.broadcast(f"Scheduled start in {delay:.2f} seconds")

                asyncio.create_task(self._delayed_broadcast(
                    file_path, filename, frequency, ps, rt, pi, loop, delay
                ))

                await self.proto.reply(parsed, Commands.OK, message=f"Scheduled in {delay:.2f}s")
                return

        started = await self._start_broadcast(file_path, filename, frequency, ps, rt, pi, loop)

        if isinstance(started, Exception):
            await self.proto.reply(parsed, Commands.ERROR, message=str(started))
        else:
            await self.proto.reply(parsed, Commands.OK, message="Broadcast started")

    async def _handle_stream_token(self, parsed: dict):
        kwargs = parsed["kwargs"]

        token = kwargs.get('token')
        rate = int(kwargs.get('rate', 48000))
        channels = int(kwargs.get('channels', 2))

        # Broadcast params
        frequency = float(kwargs.get('frequency', 90.0))
        ps = kwargs.get('ps', 'BotWave')
        rt = kwargs.get('rt', 'Streaming')
        pi = kwargs.get('pi', 'FFFF')

        if not token:
            await self.proto.reply(parsed, Commands.ERROR, message="Missing token")
            return

        Log.broadcast(f"Received stream token (rate={rate}, channels={channels})")

        started = await self._start_stream_broadcast(token, rate, channels, frequency, ps, rt, pi)

        if isinstance(started, Exception):
            await self.proto.reply(parsed, Commands.ERROR, message=str(started))
        else:
            await self.proto.reply(parsed, Commands.OK, message="Stream broadcast started")


    async def _start_stream_broadcast(self, token, rate, channels, frequency, ps, rt, pi):
        async def finished():
            Log.info("Stream finished, stopping broadcast...")
            await self._stop_broadcast()

        async with self.broadcast_lock:
            if self.broadcasting:
                await self._stop_broadcast(acquire_lock=False)

            try:
                self.piwave = PiWave(
                    frequency=frequency,
                    ps=ps,
                    rt=rt,
                    pi=pi,
                    loop=False,
                    backend="bw_custom",
                    debug=not self.silent,
                    silent=self.silent
                )

                self.stream_task = self.http_client.stream_pcm_generator(
                    server_host=self.http_host,
                    server_port=self.http_port,
                    token=token,
                    rate=rate,
                    channels=channels,
                    chunk_size=1024
                )
                captured = self.stream_task
                self.stream_active = True

                stream_queue = queue.Queue(maxsize=50)

                async def _feed_queue():
                    try:
                        async for chunk in captured:
                            if not self.stream_active:
                                break
                            stream_queue.put(chunk)
                    except Exception as e:
                        Log.error(f"Stream feed error: {e}")
                    finally:
                        stream_queue.put(None)  # sentinel

                asyncio.get_event_loop().create_task(_feed_queue())

                def sync_generator_wrapper():
                    try:
                        while self.stream_active:
                            try:
                                chunk = stream_queue.get(timeout=5)
                                if chunk is None:
                                    break
                                yield chunk

                            except queue.Empty:
                                Log.warning("Stream stalled (queue timeout)")
                                break
                    except GeneratorExit:
                        pass
                    finally:
                        self.stream_active = False

                self.broadcasting = True
                self.current_file = f"stream:{token[:8]}"

                success = self.piwave.play(
                    sync_generator_wrapper(),
                    sample_rate=rate,
                    channels=channels,
                    chunk_size=1024
                )

                self.piwave_monitor.start(self.piwave, finished, asyncio.get_event_loop())

                if success:
                    Log.broadcast(f"Broadcasting stream on {frequency} MHz (rate={rate}, channels={channels})")
                else:
                    Log.warning(f"PiWave returned a non-true status ?")

                return True

            except Exception as e:
                Log.error(f"Stream broadcast error: {e}")
                self.broadcasting = False
                return e

    async def _delayed_broadcast(self, file_path, filename, frequency, ps, rt, pi, loop, delay):
        await asyncio.sleep(delay)
        started = await self._start_broadcast(file_path, filename, frequency, ps, rt, pi, loop)

        if isinstance(started, Exception):
            await self.proto.fire(Commands.ERROR, message=str(started))
        else:
            await self.proto.fire(Commands.OK, message="Broadcast started")


    async def _start_broadcast(self, file_path, filename, frequency, ps, rt, pi, loop):
        async def finished():
            Log.info("Playback finished, stopping broadcast...")

            try:
                await self.proto.fire(
                    Commands.END,
                    filename=filename
                )
            except Exception as e:
                Log.error(f"Error notifying server of broadcast end: {e}")

            await self._stop_broadcast()

        async with self.broadcast_lock:
            if self.broadcasting:
                await self._stop_broadcast(acquire_lock=False)

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

                success = self.piwave.play(file_path, blocking=False)

                self.broadcasting = True
                self.current_file = filename

                if not loop:
                    self.piwave_monitor.start(self.piwave, finished, asyncio.get_event_loop())

                if success:
                    Log.broadcast(f"Currently broadcasting {filename} on {frequency} MHz")
                else:
                    Log.warning(f"PiWave returned a non-true status ?")

                return True

            except Exception as e:
                Log.error(f"Broadcast error: {e}")
                self.broadcasting = False
                return e

    async def _stop_broadcast(self, acquire_lock=True):
        async def _cleanup():
            self.piwave_monitor.stop()

            if self.stream_active:
                self.stream_active = False
                await asyncio.sleep(0.2)

            if self.stream_task:
                try:
                    self.stream_task = None
                    Log.broadcast("Stream closed")
                except Exception as e:
                    Log.error(f"Error closing stream: {e}")
                finally:
                    self.stream_task = None

            if self.piwave:
                try:
                    self.piwave.cleanup()  # stops AND cleanups
                except Exception as e:
                    Log.error(f"Error stopping PiWave: {e}")
                finally:
                    self.piwave = None

            self.broadcasting = False
            self.current_file = None

        if acquire_lock:
            async with self.broadcast_lock:
                await _cleanup()
        else:
            await _cleanup()

        Log.broadcast("Stopped broadcast")

    async def _handle_list_files(self, parsed: dict):
        try:
            wav_files = []

            for filename in os.listdir(self.upload_dir):
                if filename.lower().endswith('.wav'):
                    file_path = os.path.join(self.upload_dir, filename)
                    if os.path.isfile(file_path):
                        stat_info = os.stat(file_path)
                        wav_files.append({
                            'name': filename,
                            'size': stat_info.st_size,
                            'modified': datetime.fromtimestamp(stat_info.st_mtime).isoformat()
                        })

            wav_files.sort(key=lambda x: x['name'])

            await self.proto.reply(
                parsed,
                Commands.OK,
                message=f"Found {len(wav_files)} files",
                files=json.dumps(wav_files)
            )
            Log.file(f"Listed {len(wav_files)} files")

        except Exception as e:
            await self.proto.reply(parsed, Commands.ERROR, str(e))

    async def _handle_remove_file(self, parsed: dict):
        kwargs = parsed["kwargs"]
        filename = kwargs.get('filename')

        if not filename:
            await self.proto.reply(parsed, Commands.ERROR, message="Missing filename")
            return

        try:
            if filename.lower() == 'all':
                removed = 0
                for f in os.listdir(self.upload_dir):
                    if f.lower().endswith('.wav'):
                        os.remove(os.path.join(self.upload_dir, f))
                        removed += 1

                Log.success(f"Removed {removed} files")
                await self.proto.reply(parsed, Commands.OK, message=f"Removed {removed} files")

            else:
                try:
                    filename = PathValidator.sanitize_filename(filename)
                    file_path = PathValidator.safe_join(self.upload_dir, filename)
                except SecurityError as e:
                    Log.error(f"Security violation in remove: {e}")
                    await self.proto.reply(parsed, Commands.ERROR, message="Provided filename raised a security violation")
                    return

                if not os.path.exists(file_path):
                    await self.proto.reply(parsed, Commands.ERROR, message="File not found")
                else:
                    os.remove(file_path)
                    Log.success(f"Removed: {filename}")
                    await self.proto.reply(parsed, Commands.OK, message=f"Removed {filename}")

        except Exception as e:
            await self.proto.reply(parsed, Commands.ERROR, message=str(e))


    async def _handle_stop_broadcast(self, parsed: dict):

        try:
            if not self.broadcasting:
                await self.proto.reply(parsed, Commands.ERROR, message="No broadcast running")
                return

            await self._stop_broadcast()

            await self.proto.reply(parsed, Commands.OK, message="Broadcast stopped")

        except Exception as e:
            Log.error(f"Stop error: {e}")
            await self.proto.reply(parsed, Commands.ERROR, message=str(e))

    async def stop(self):
        if not self.running:
            return

        self.running = False

        if self.broadcasting:
            await self._stop_broadcast()

        if self.piwave:
            self.piwave.cleanup()

        if self.ws_client:
            await self.ws_client.disconnect()

        self.tips.stop()

        Log.client("Client stopped")


def main():
    Log.header("BotWave - Client")

    check()

    parser = argparse.ArgumentParser(description='BotWave Client')
    parser.add_argument('server_host', nargs='?', help='Server hostname/IP')
    parser.add_argument('--port', type=int, default=None, help='Server port')
    parser.add_argument('--fhost', help='File transfer server hostname/IP (defaults to server_host)')
    parser.add_argument('--fport', type=int, default=None, help='File transfer (HTTP) port')
    parser.add_argument('--upload-dir', default=None, help='Uploads directory')
    parser.add_argument('--pk', help='Passkey for authentication')
    parser.add_argument('--skip-checks', dest='skip_checks', action=argparse.BooleanOptionalAction, default=None, help='Skip update and requirements checks')
    parser.add_argument('--talk', action=argparse.BooleanOptionalAction, default=None, help='Makes PiWave (broadcast manager) output logs visible.')
    args = parser.parse_args()

    # Set the env from the params

    def set_prio(key, cli_value, default, immutable=False): # helper to set with priority
        if cli_value is not None:
            Env.set(key, str(cli_value), immutable=immutable)

        elif not Env.get(key, False):
            Env.set(key, str(default), immutable=immutable)

    if args.server_host:
        Env.set("SERVER_HOST", args.server_host, immutable=True)
    elif not Env.get("SERVER_HOST", False):
        Env.set("SERVER_HOST", input("Server hostname/IP: ").strip(), immutable=True)

    set_prio("SERVER_PORT", args.port, 9938, immutable=True)
    set_prio("FHOST", args.fhost, Env.get("SERVER_HOST"), immutable=True)
    set_prio("FPORT", args.fport, 9921, immutable=True)
    set_prio("UPLOAD_DIR", args.upload_dir, '/opt/BotWave/uploads/')
    set_prio("TALK", args.talk, False)
    set_prio("SKIP_CHECKS", args.skip_checks, False)

    if args.pk:
        Env.set("PASSKEY", args.pk, immutable=True)

    if not Env.get_bool("SKIP_CHECKS"):
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

    client = BotWaveClient()

    try:
        asyncio.run(client.start())
    except KeyboardInterrupt:
        Log.warning("Interrupted")

if __name__ == "__main__":
    main()