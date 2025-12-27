import aiofiles
import asyncio
import os
import ssl
import time
import uuid
from aiohttp import web, ClientSession, TCPConnector
from typing import Dict, Optional, AsyncIterator
from shared.logger import Log

CHUNK_SIZE = 65536 # 64KB, here so we have the value centralized

class BWHTTPFileServer:
    
    # http server for downloads / uploads / pcm streaming
    # each file has a time-limited unique id
    
    def __init__(
        self,
        host: str,
        port: int,
        ssl_context: ssl.SSLContext,
        upload_dir: str,
        token_lifetime: int = 300
    ):

        self.host = host
        self.port = port
        self.ssl_context = ssl_context
        self.upload_dir = upload_dir
        self.token_lifetime = token_lifetime

        self.upload_tokens: Dict[str, dict] = {}
        self.download_tokens: Dict[str, dict] = {}
        self.stream_tokens: Dict[str, dict] = {}
        
        self.app = None
        self.runner = None
        
        os.makedirs(upload_dir, exist_ok=True)
        
        asyncio.create_task(self._cleanup_expired_tokens())
    
    def create_upload_token(self, filename: str, size: int) -> str:
        token = uuid.uuid4().hex
        self.upload_tokens[token] = {
            'filename': filename,
            'size': size,
            'expires': time.time() + self.token_lifetime
        }
        return token
    
    def create_download_token(self, filepath: str) -> str:
        token = uuid.uuid4().hex
        self.download_tokens[token] = {
            'filepath': filepath,
            'expires': time.time() + self.token_lifetime
        }
        return token
    
    def create_stream_token(self, audio_generator, rate: int = 48000, channels: int = 2) -> str:
        token = uuid.uuid4().hex
        self.stream_tokens[token] = {
            'generator': audio_generator,
            'rate': rate,
            'channels': channels,
            'expires': time.time() + self.token_lifetime
        }
        return token
    
    async def start(self):
        self.app = web.Application(client_max_size=1024**3)  # max 1gb
        
        self.app.router.add_post('/upload/{token}', self._handle_upload)
        self.app.router.add_get('/download/{token}', self._handle_download)
        self.app.router.add_get('/stream/{token}', self._handle_pcm_stream)
        
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        
        site = web.TCPSite(
            self.runner,
            self.host,
            self.port,
            ssl_context=self.ssl_context
        )
        await site.start()
        
        Log.server(f"HTTP file server started on https://{self.host}:{self.port}")
    
    async def stop(self):
        if self.runner:
            await self.runner.cleanup()
    
    async def _handle_upload(self, request: web.Request) -> web.Response:
        token = request.match_info['token']
        
        if token not in self.upload_tokens:
            return web.Response(status=404, text="Invalid token")
        
        token_data = self.upload_tokens[token]
        
        if time.time() > token_data['expires']:
            del self.upload_tokens[token]
            return web.Response(status=403, text="Token expired")
        
        filename = token_data['filename']
        expected_size = token_data['size']
        filepath = os.path.join(self.upload_dir, filename)
        
        try:
            bytes_received = 0
            
            async with aiofiles.open(filepath, 'wb') as f:
                async for chunk in request.content.iter_chunked(CHUNK_SIZE):
                    await f.write(chunk)
                    bytes_received += len(chunk)
            
            actual_size = os.path.getsize(filepath)
            
            if expected_size > 0 and actual_size != expected_size:
                os.remove(filepath)
                return web.Response(
                    status=400,
                    text=f"Size mismatch: expected {expected_size}, got {actual_size}"
                )
            
            del self.upload_tokens[token]
            
            return web.Response(status=200, text="Upload successful")
        
        except Exception as e:
            # cleanup partial files
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except:
                    pass
            
            return web.Response(status=500, text=f"Upload error: {str(e)}")
    
    async def _handle_download(self, request: web.Request) -> web.StreamResponse:
        token = request.match_info['token']
        
        if token not in self.download_tokens:
            return web.Response(status=404, text="Invalid or expired token")
        
        token_data = self.download_tokens[token]
        
        if time.time() > token_data['expires']:
            del self.download_tokens[token]
            return web.Response(status=403, text="Token expired")
        
        filepath = token_data['filepath']
        
        if not os.path.exists(filepath):
            del self.download_tokens[token]
            return web.Response(status=404, text="File not found")
        
        try:
            file_size = os.path.getsize(filepath)
            filename = os.path.basename(filepath)
            
            response = web.StreamResponse(
                status=200,
                headers={
                    'Content-Type': 'application/octet-stream',
                    'Content-Disposition': f'attachment; filename="{filename}"',
                    'Content-Length': str(file_size)
                }
            )
            
            await response.prepare(request)
            
            async with aiofiles.open(filepath, 'rb') as f:
                while True:
                    chunk = await f.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    await response.write(chunk)
            
            await response.write_eof()
            
            del self.download_tokens[token]
            
            return response
        
        except Exception as e:
            return web.Response(status=500, text=f"Download error: {str(e)}")
    
    async def _handle_pcm_stream(self, request: web.Request) -> web.StreamResponse:
        token = request.match_info['token']
        
        if token not in self.stream_tokens:
            return web.Response(status=404, text="Invalid token")
        
        token_data = self.stream_tokens[token]
        
        if time.time() > token_data['expires']:
            del self.stream_tokens[token]
            return web.Response(status=403, text="Token expired")
        
        audio_generator = token_data['generator']
        rate = token_data.get('rate', 48000)
        channels = token_data.get('channels', 2)
        
        response = web.StreamResponse(
            status=200,
            headers={
                'Content-Type': 'audio/pcm',
                'Cache-Control': 'no-cache',
                'X-Sample-Rate': str(rate),
                'X-Channels': str(channels),
                'X-Sample-Format': 'S16_LE'
            }
        )
        
        await response.prepare(request)
        
        try:
            loop = asyncio.get_event_loop()
            
            async for pcm_chunk in self._async_generator_wrapper(audio_generator, loop):
                if pcm_chunk:
                    await response.write(pcm_chunk)
                    await response.drain()
                
                if request.transport is None or request.transport.is_closing():
                    Log.server("Client disconnected from PCM stream")
                    break
                    
        except asyncio.CancelledError:
            Log.server("PCM stream cancelled")
        except Exception as e:
            Log.error(f"PCM stream error: {e}")
        finally:
            try:
                await response.write_eof()
            except:
                pass
            
            if token in self.stream_tokens:
                del self.stream_tokens[token]
        
        return response
    
    async def _async_generator_wrapper(self, sync_generator, loop):
        import concurrent.futures
        
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        
        try:
            while True:
                try:
                    chunk = await loop.run_in_executor(executor, next, sync_generator, None)
                    
                    if chunk is None:
                        break
                    
                    yield chunk
                    
                except StopIteration:
                    break
                except Exception as e:
                    Log.error(f"Generator error: {e}")
                    break
        finally:
            executor.shutdown(wait=False)
    
    async def _cleanup_expired_tokens(self):
        while True:
            await asyncio.sleep(300)
            
            current_time = time.time()
            
            expired_upload = [
                token for token, data in self.upload_tokens.items()
                if current_time > data['expires']
            ]
            for token in expired_upload:
                del self.upload_tokens[token]
            
            expired_download = [
                token for token, data in self.download_tokens.items()
                if current_time > data['expires']
            ]
            for token in expired_download:
                del self.download_tokens[token]
            
            expired_stream = [
                token for token, data in self.stream_tokens.items()
                if current_time > data['expires']
            ]
            for token in expired_stream:
                del self.stream_tokens[token]


class BWHTTPFileClient:
    
    def __init__(self, ssl_context: ssl.SSLContext):
        self.ssl_context = ssl_context
    
    async def upload_file(self, server_host: str, server_port: int, token: str, filepath: str, progress_callback: Optional[callable] = None) -> bool:

        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")
        
        file_size = os.path.getsize(filepath)
        url = f"https://{server_host}:{server_port}/upload/{token}"
        
        try:
            # ssl connector that ignores self-signed certs
            connector = TCPConnector(ssl=self.ssl_context)
            
            async with ClientSession(connector=connector) as session:
                async with aiofiles.open(filepath, 'rb') as f:
                    # Create async generator for chunked upload
                    async def file_sender():
                        bytes_sent = 0
                        while True:
                            chunk = await f.read(CHUNK_SIZE)
                            if not chunk:
                                break
                            bytes_sent += len(chunk)
                            
                            if progress_callback:
                                progress_callback(bytes_sent, file_size)
                            
                            yield chunk
                    
                    async with session.post(url, data=file_sender()) as response:
                        if response.status == 200:
                            return True
                        else:
                            error_text = await response.text()
                            Log.error(f"Upload failed: {error_text}")
                            return False
        
        except Exception as e:
            Log.error(f"Upload error: {e}")
            return False
    
    async def download_file(self, server_host: str, server_port: int, token: str, save_path: str, progress_callback: Optional[callable] = None) -> bool:
        url = f"https://{server_host}:{server_port}/download/{token}"
        
        try:
            # Create SSL connector that ignores self-signed certs
            connector = TCPConnector(ssl=self.ssl_context)
            
            async with ClientSession(connector=connector) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        Log.error(f"Download failed: {error_text}")
                        return False
                    
                    total_size = int(response.headers.get('Content-Length', 0))
                    
                    bytes_received = 0
                    
                    async with aiofiles.open(save_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(65536):
                            await f.write(chunk)
                            bytes_received += len(chunk)
                            
                            if progress_callback:
                                progress_callback(bytes_received, total_size)
                    
                    return True
        
        except Exception as e:
            Log.error(f"Download error: {e}")
            return False
        
    async def stream_pcm_generator(self, server_host: str, server_port: int, token: str, rate: int = 48000, channels: int = 2, chunk_size: int = 1024):
        url = f"https://{server_host}:{server_port}/stream/{token}"
        
        try:
            connector = TCPConnector(ssl=self.ssl_context)
            
            async with ClientSession(connector=connector) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        Log.error(f"Stream failed: {error_text}")
                        return
                    
                    Log.success(f"Connected to PCM stream (rate={rate}, channels={channels})")
                    
                    async for chunk in response.content.iter_chunked(chunk_size * channels * 2):
                        yield chunk
                    
                    Log.info("Stream ended")
                    
        except Exception as e:
            Log.error(f"Stream error: {e}")
            return