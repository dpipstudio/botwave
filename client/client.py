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
from datetime import datetime, timezone
import json
import os
import platform
import sys
import urllib.request
import asyncio
import ssl
import sys
import os
from datetime import datetime, timezone

# using this to access to the shared dir files
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from shared.alsa import Alsa
from shared.bw_custom import BWCustom
from shared.cat import check
from shared.http import BWHTTPFileClient
from shared.logger import Log
from shared.protocol import ProtocolParser, Commands, PROTOCOL_VERSION
from shared.pw_monitor import PWM
from shared.socket import BWWebSocketClient
from shared.syscheck import check_requirements
from shared.version import check_for_updates


try:
    from piwave import PiWave
    from piwave.backends import backend_classes
except ImportError:
    Log.error("PiWave module not found. Please install it first.")
    sys.exit(1)


class BotWaveClient:
    def __init__(self, server_host: str, ws_port: int, http_port: int, http_host: str = None, upload_dir: str = "/opt/BotWave/uploads", passkey: str = None):
        self.server_host = server_host
        self.http_host = http_host or server_host
        self.ws_port = ws_port
        self.http_port = http_port
        self.upload_dir = upload_dir
        self.passkey = passkey
        
        # communications
        self.ws_client = None
        self.http_client = None
        
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
        
        os.makedirs(upload_dir, exist_ok=True)
        backend_classes["bw_custom"] = BWCustom

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
        
        register_cmd = ProtocolParser.build_command(
            Commands.REGISTER,
            hostname=machine_info['hostname'],
            machine=machine_info['machine'],
            system=machine_info['system'],
            release=machine_info['release']
        )
        
        await self.ws_client.send(register_cmd)
        
        # if passkey, sending auth cmd
        if self.passkey:
            auth_cmd = ProtocolParser.build_command(Commands.AUTH, self.passkey)
            await self.ws_client.send(auth_cmd)
        
        ver_cmd = ProtocolParser.build_command(Commands.VER, PROTOCOL_VERSION)
        await self.ws_client.send(ver_cmd)
        
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
                host=self.server_host,
                port=self.ws_port,
                ssl_context=ssl_context,
                on_message_callback=self._handle_server_msg
            )
            
            self.http_client = BWHTTPFileClient(ssl_context=ssl_context)
            
            if not await self.connect():
                await self.stop()
            
            self.running = True
            
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
                await self.ws_client.send(Commands.PONG)
                return
            
            # broadcast
            if command == Commands.START:
                await self._handle_start_broadcast(kwargs)
                return
            
            if command == Commands.STREAM_TOKEN:
                await self._handle_stream_token(kwargs)
                return
            
            if command == Commands.STOP:
                await self._handle_stop_broadcast()
                return
            
            # files
            if command == Commands.UPLOAD_TOKEN:
                await self._handle_upload_token(kwargs)
                return
            
            if command == Commands.DOWNLOAD_TOKEN:
                await self._handle_download_token(kwargs)
                return
            
            if command == Commands.DOWNLOAD_URL:
                await self._handle_download_url(kwargs)
                return
            
            # files managment
            if command == Commands.LIST_FILES:
                await self._handle_list_files()
                return
            
            if command == Commands.REMOVE_FILE:
                await self._handle_remove_file(kwargs)
                return
            
            # client managment
            if command == Commands.KICK:
                reason = kwargs.get('reason', 'Kicked by administrator')
                Log.warning(f"Kicked: {reason}")
                await self.stop()
                return
            
            Log.warning(f"Unknown command: {command}")
            response = ProtocolParser.build_response(Commands.ERROR, message=f"Unknown command: {command}. Perhaps a protocol mismatch ?")
            await self.ws_client.send(response)
            
        except Exception as e:
            Log.error(f"Error handling message: {e}")

    async def _handle_upload_token(self, kwargs: dict):
        token = kwargs.get('token')
        filename = kwargs.get('filename')
        size = int(kwargs.get('size', 0))
        
        if not token or not filename:
            error = ProtocolParser.build_response(Commands.ERROR, "Missing token or filename")
            await self.ws_client.send(error)
            return
        
        Log.file(f"Received upload token for: {filename} ({size if size > 0 else '?'} bytes)")
        
        def progress(bytes_sent, total):
            if total > 0:
                Log.progress_bar(bytes_sent, total, prefix=f'Uploading {filename}:', suffix='Complete', style='yellow', icon='FILE', auto_clear=(bytes_sent == total))
        
        success = await self.http_client.upload_file(
            server_host=self.http_host,
            server_port=self.http_port,
            token=token,
            filepath=os.path.join(self.upload_dir, filename),
            progress_callback=progress
        )
        
        if success:
            Log.success(f"Upload completed: {filename}")
            response = ProtocolParser.build_response(Commands.OK, f"Uploaded {filename}")
        else:
            Log.error(f"Upload failed: {filename}")
            response = ProtocolParser.build_response(Commands.ERROR, "Upload failed")
        
        await self.ws_client.send(response)
        

    async def _handle_download_token(self, kwargs: dict):
        token = kwargs.get('token')
        filename = kwargs.get('filename')
        
        if not token or not filename:
            error = ProtocolParser.build_response(Commands.ERROR, "Missing token or filename")
            await self.ws_client.send(error)
            return
        
        Log.file(f"Received download token for: {filename}")
        
        save_path = os.path.join(self.upload_dir, filename)
        
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
            response = ProtocolParser.build_response(Commands.OK, f"Downloaded {filename}")
        else:
            Log.error(f"Download failed: {filename}")
            response = ProtocolParser.build_response(Commands.ERROR, "Download failed")
        
        await self.ws_client.send(response)

    async def _handle_download_url(self, kwargs: dict):
        url = kwargs.get('url')
        filename = kwargs.get('filename')
        
        if not url or not filename:
            error = ProtocolParser.build_response(Commands.ERROR, "Missing URL or filename")
            await self.ws_client.send(error)
            return
        
        filepath = os.path.join(self.upload_dir, filename)
        
        try:
            Log.file(f"Downloading from URL: {url}")
            
            def download_with_progress():
                urllib.request.urlretrieve(url, filepath)
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, download_with_progress)
            
            if os.path.exists(filepath):
                file_size = os.path.getsize(filepath)
                Log.success(f"Downloaded: {filename} ({file_size if file_size > 0 else '?'} bytes)")
                response = ProtocolParser.build_response(Commands.OK, f"Downloaded {filename}")

            else:
                Log.error(f"Download failed: file not created")
                response = ProtocolParser.build_response(Commands.ERROR, "File not created")
                
        except urllib.error.URLError as e:
            Log.error(f"Network error: {e}")
            response = ProtocolParser.build_response(Commands.ERROR, f"Network error: {str(e)}")
        except Exception as e:
            Log.error(f"Download failed: {e}")
            response = ProtocolParser.build_response(Commands.ERROR, str(e))
        
        await self.ws_client.send(response)
        
    async def _handle_start_broadcast(self, kwargs: dict):
        filename = kwargs.get('filename')
        if not filename:
            response = ProtocolParser.build_response(Commands.ERROR, "Missing filename")
            await self.ws_client.send(response)
            return
        
        file_path = os.path.join(self.upload_dir, filename)
        if not os.path.exists(file_path):
            response = ProtocolParser.build_response(Commands.END, f"File not found: {filename}")
            await self.ws_client.send(response)
            return
        
        # broadcast params
        frequency = float(kwargs.get('freq', 90.0))
        ps = kwargs.get('ps', 'BotWave')
        rt = kwargs.get('rt', 'Broadcasting')
        pi = kwargs.get('pi', 'FFFF')
        loop = kwargs.get('loop', 'false').lower() == 'true'
        start_at = float(kwargs.get('start_at', 0))
        
        # handle delayed start
        if start_at > 0:
            current_time = datetime.now(timezone.utc).timestamp()
            if start_at > current_time:
                delay = start_at - current_time
                Log.broadcast(f"Scheduled start in {delay:.2f} seconds")
                
                asyncio.create_task(self._delayed_broadcast(
                    file_path, filename, frequency, ps, rt, pi, loop, delay
                ))
                
                response = ProtocolParser.build_response(Commands.OK, f"Scheduled in {delay:.2f}s")
                await self.ws_client.send(response)
                return
        
        # "start asap"
        started = await self._start_broadcast(file_path, filename, frequency, ps, rt, pi, loop)

        if isinstance(started, Exception):
            response = ProtocolParser.build_response(Commands.ERROR, message=str(started));
        else:
            response = ProtocolParser.build_response(Commands.OK, "Broadcast started")

        await self.ws_client.send(response)

    async def _handle_stream_token(self, kwargs: dict):
        token = kwargs.get('token')
        rate = int(kwargs.get('rate', 48000))
        channels = int(kwargs.get('channels', 2))
        
        # Broadcast params
        frequency = float(kwargs.get('frequency', 90.0))
        ps = kwargs.get('ps', 'BotWave')
        rt = kwargs.get('rt', 'Streaming')
        pi = kwargs.get('pi', 'FFFF')
        
        if not token:
            error = ProtocolParser.build_response(Commands.ERROR, "Missing token")
            await self.ws_client.send(error)
            return
        
        Log.broadcast(f"Received stream token (rate={rate}, channels={channels})")
        
        started = await self._start_stream_broadcast(token, rate, channels, frequency, ps, rt, pi)
        
        if isinstance(started, Exception):
            response = ProtocolParser.build_response(Commands.ERROR, message=str(started))
        else:
            response = ProtocolParser.build_response(Commands.OK, "Stream broadcast started")
        
        await self.ws_client.send(response)

    async def _start_stream_broadcast(self, token, rate, channels, frequency, ps, rt, pi):
        async def finished():
            Log.info("Stream finished, stopping broadcast...")
            await self._stop_broadcast()
        
        async with self.broadcast_lock:
            if self.broadcasting:
                await self._stop_broadcast()
            
            try:
                self.piwave = PiWave(
                    frequency=frequency,
                    ps=ps,
                    rt=rt,
                    pi=pi,
                    loop=False,
                    backend="bw_custom",
                    debug=False
                )
                
                stream_task = self.http_client.stream_pcm_generator(
                    server_host=self.http_host,
                    server_port=self.http_port,
                    token=token,
                    rate=rate,
                    channels=channels,
                    chunk_size=1024
                )

                self.stream_active = True
                
                def sync_generator_wrapper():
                    loop = asyncio.new_event_loop()
                    try:
                        async_gen = self.stream_task.__aiter__()
                        while self.stream_active:
                            try:
                                chunk = loop.run_until_complete(
                                    asyncio.wait_for(async_gen.__anext__(), timeout=5.0)
                                )
                                yield chunk
                            except asyncio.TimeoutError:
                                if not self.stream_active:
                                    break
                                continue
                            except StopAsyncIteration:
                                break
                    except Exception as e:
                        Log.error(f"Stream generator error: {e}")
                    finally:
                        loop.close()
                
                self.broadcasting = True
                self.current_file = f"stream:{token[:8]}"
                
                self.stream_task = stream_task
                
                self.piwave.play(
                    sync_generator_wrapper(),
                    sample_rate=rate,
                    channels=channels,
                    chunk_size=1024
                )
                
                self.piwave_monitor.start(self.piwave, finished, asyncio.get_event_loop())
                
                Log.broadcast(f"Broadcasting stream on {frequency} MHz (rate={rate}, channels={channels})")
                return True
                
            except Exception as e:
                Log.error(f"Stream broadcast error: {e}")
                self.broadcasting = False
                return e

    async def _delayed_broadcast(self, file_path, filename, frequency, ps, rt, pi, loop, delay):
        await asyncio.sleep(delay)
        started = await self._start_broadcast(file_path, filename, frequency, ps, rt, pi, loop)

        if isinstance(started, Exception):
            response = ProtocolParser.build_response(Commands.ERROR, message=str(started));
        else:
            response = ProtocolParser.build_response(Commands.OK, "Broadcast started")

        await self.ws_client.send(response)


    async def _start_broadcast(self, file_path, filename, frequency, ps, rt, pi, loop):
        async def finished():
            Log.info("Playback finished, stopping broadcast...")

            try:
                response = ProtocolParser.build_command(
                    Commands.END,
                    filename=filename
                )
                await self.ws_client.send(response)
            except Exception as e:
                Log.error(f"Error notifying server of broadcast end: {e}")

            await self._stop_broadcast()

        async with self.broadcast_lock:
            if self.broadcasting:
                await self._stop_broadcast()

            try:
                self.piwave = PiWave(
                    frequency=frequency,
                    ps=ps,
                    rt=rt,
                    pi=pi,
                    loop=loop,
                    backend="bw_custom",
                    debug=False
                )

                self.piwave.play(file_path, blocking=False)

                self.broadcasting = True
                self.current_file = filename

                if not loop:
                    self.piwave_monitor.start(self.piwave, finished, asyncio.get_event_loop())

                Log.broadcast(f"Broadcasting: {filename} on {frequency} MHz")
                return True

            except Exception as e:
                Log.error(f"Broadcast error: {e}")
                self.broadcasting = False
                return e

    async def _stop_broadcast(self):
        async with self.broadcast_lock:
            self.piwave_monitor.stop()

            if self.stream_active:
                self.stream_active = False
                await asyncio.wait(0.2)

            if self.stream_task:
                try:
                    await asyncio.sleep(0.1)
                    await self.stream_task.aclose()
                    Log.broadcast("Stream closed")
                except Exception as e:
                    Log.error(f"Error closing stream: {e}")
                finally:
                    self.stream_task = None

            if self.piwave:
                try:
                    self.piwave.cleanup() # stops AND cleanups
                    Log.broadcast("PiWave stopped")
                except Exception as e:
                    Log.error(f"Error stopping PiWave: {e}")
                finally:
                    self.piwave = None
            
            self.broadcasting = False
            self.current_file = None

    async def _handle_list_files(self):
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
            
            response = ProtocolParser.build_command(
                Commands.OK,
                message=f"Found {len(wav_files)} files",
                files=json.dumps(wav_files)
            )
            
            await self.ws_client.send(response)
            Log.file(f"Listed {len(wav_files)} files")
            
        except Exception as e:
            error = ProtocolParser.build_response(Commands.ERROR, str(e))
            await self.ws_client.send(error)

    async def _handle_remove_file(self, kwargs: dict):
        filename = kwargs.get('filename')
        
        if not filename:
            response = ProtocolParser.build_response(Commands.ERROR, "Missing filename")
            await self.ws_client.send(response)
            return
        
        try:
            if filename.lower() == 'all':
                removed = 0
                for f in os.listdir(self.upload_dir):
                    if f.lower().endswith('.wav'):
                        os.remove(os.path.join(self.upload_dir, f))
                        removed += 1
                
                Log.success(f"Removed {removed} files")
                response = ProtocolParser.build_response(Commands.OK, f"Removed {removed} files")
            else:
                file_path = os.path.join(self.upload_dir, filename)
                if not os.path.exists(file_path):
                    response = ProtocolParser.build_response(Commands.ERROR, "File not found")
                else:
                    os.remove(file_path)
                    Log.success(f"Removed: {filename}")
                    response = ProtocolParser.build_response(Commands.OK, f"Removed {filename}")
            
            await self.ws_client.send(response)
            
        except Exception as e:
            error = ProtocolParser.build_response(Commands.ERROR, str(e))
            await self.ws_client.send(error)


    async def _handle_stop_broadcast(self):
        try:
            if not self.broadcasting:
                response = ProtocolParser.build_response(Commands.ERROR, "No broadcast running")
                await self.ws_client.send(response)
                return
            
            await self._stop_broadcast()
            
            response = ProtocolParser.build_response(Commands.OK, "Broadcast stopped")
            await self.ws_client.send(response)
            
        except Exception as e:
            Log.error(f"Stop error: {e}")
            error = ProtocolParser.build_response(Commands.ERROR, str(e))
            await self.ws_client.send(error)

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
        
        Log.client("Client stopped")


def main():
    Log.header("BotWave - Client")

    check() # most important check

    parser = argparse.ArgumentParser(description='BotWave Client')
    parser.add_argument('server_host', nargs='?', help='Server hostname/IP')
    parser.add_argument('--port', type=int, default=9938, help='Server port')
    parser.add_argument('--fhost', help='File transfer server hostname/IP (defaults to server_host)')
    parser.add_argument('--fport', type=int, default=9921, help='File transfer (HTTP) port')
    parser.add_argument('--upload-dir', default='/opt/BotWave/uploads', help='Uploads directory')
    parser.add_argument('--pk', help='Passkey for authentication')
    parser.add_argument('--skip-checks', action='store_true', help='Skip update and requirements checks')
    args = parser.parse_args()
    
    if not args.server_host:
        args.server_host = input("Server hostname/IP: ").strip()
    
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
    
    client = BotWaveClient(
        server_host=args.server_host,
        ws_port=args.port,
        http_port=args.fport,
        http_host=args.fhost,
        upload_dir=args.upload_dir,
        passkey=args.pk
    )
    
    try:
        asyncio.run(client.start())
    except KeyboardInterrupt:
        Log.warning("Interrupted")

if __name__ == "__main__":
    main()