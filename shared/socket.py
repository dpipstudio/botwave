import asyncio
import ssl
import websockets
from typing import Any, Awaitable, Callable
from websockets.exceptions import ConnectionClosed
from websockets.legacy.client import WebSocketClientProtocol
from websockets.legacy.server import WebSocketServerProtocol

from shared.env import Env
from shared.logger import Log

PING_INTERVAL = 30
PING_TIMEOUT = 5

class BWWebSocketServer:
    def __init__(self, ssl_context: ssl.SSLContext, on_message_callback: Callable[..., Awaitable[Any]], on_connect_callback: Callable[..., Awaitable[Any]], on_disconnect_callback: Callable[..., Awaitable[Any]]):
        self.ssl_context = ssl_context
        self.on_message = on_message_callback
        self.on_connect = on_connect_callback
        self.on_disconnect = on_disconnect_callback
        
        # client_id -> ws
        self.clients: dict[str, WebSocketServerProtocol] = {}
        
        self.pending_clients: dict[WebSocketServerProtocol, dict[Any, Any]] = {}
        
        self.server = None
        self.running = False

    @property
    def host(self):
        return Env.get("HOST", "0.0.0.0")
    
    @property
    def port(self):
        return Env.get_int("PORT", 9938)
    
    async def start(self):
        self.running = True
        self.server = await websockets.serve( # pyright: ignore
            self._handle_client,
            self.host,
            self.port,
            ssl=self.ssl_context,
            ping_interval=PING_INTERVAL,
            ping_timeout=PING_TIMEOUT
        )
        Log.server(f"WebSocket server started on wss://{self.host}:{self.port}")
    
    async def stop(self):
        self.running = False
        if self.server:
            self.server.close()
            await self.server.wait_closed()
    
    async def _handle_client(self, websocket: WebSocketServerProtocol, path: str):
        client_id = None
        
        try:
            # store websocket in pending until registered
            self.pending_clients[websocket] = {}
            
            async for message in websocket:
                # not registered yet = only accept registration messages
                if client_id is None:

                    await self.on_message(None, message, websocket)
                    
                    if websocket in self.pending_clients:
                        temp_data = self.pending_clients.get(websocket, {})
                        if 'client_id' in temp_data:
                            client_id = temp_data['client_id']
                            del self.pending_clients[websocket]
                            self.clients[client_id] = websocket
                            await self.on_connect(client_id, websocket)

                else:
                    # registred = process normally
                    await self.on_message(client_id, message, websocket)
        
        except ConnectionClosed:
            pass

        except Exception as e:
            Log.error(
                f"Error handling client "
                f"({type(e).__name__}): {repr(e)}"
                )
            
        finally:
            if websocket in self.pending_clients:
                del self.pending_clients[websocket]
            
            if client_id and client_id in self.clients:
                del self.clients[client_id]
                await self.on_disconnect(client_id)
    
    def register_client(self, websocket: WebSocketServerProtocol, client_id: str):
        if websocket in self.pending_clients:
            self.pending_clients[websocket]['client_id'] = client_id
    
    async def send(self, client_id: str, message: str):
        # send a msg to a client

        if client_id in self.clients:
            try:
                await self.clients[client_id].send(message)
            except Exception as e:
                Log.error(
                    f"Error sending to {client_id} "
                    f"({type(e).__name__}): {repr(e)}"
                    )
    
    async def broadcast(self, message: str, exclude: str | None = None):
        tasks: list[Any] = []
        for client_id, websocket in self.clients.items():
            if client_id != exclude:
                tasks.append(websocket.send(message))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)


class BWWebSocketClient:    
    def __init__(self, ssl_context: ssl.SSLContext, on_message_callback: Callable[..., Awaitable[Any]]):
        self.ssl_context = ssl_context
        self.on_message = on_message_callback
        
        self.ws: WebSocketClientProtocol | None = None
        self.connected = False
        self.running = False
        
        self._receive_task = None
        self._ping_task = None

    @property
    def host(self):
        return Env.get("SERVER_HOST")
    
    @property
    def port(self):
        return Env.get_int("SERVER_PORT", 9938)
    
    async def connect(self) -> bool:

        try:
            uri = f"wss://{self.host}:{self.port}"
            self.ws = await websockets.connect( # pyright: ignore
                uri,
                ssl=self.ssl_context,
                ping_interval=PING_INTERVAL,
                ping_timeout=PING_TIMEOUT
            )
            self.connected = True
            self.running = True
            
            self._receive_task = asyncio.create_task(self._receive_loop())
            
            return True
        except Exception as e:
            Log.error(
                f"Error connecting to server "
                f"({type(e).__name__}): {repr(e)}"
            )
            return False

    
    async def disconnect(self):
        self.running = False
        
        if self._receive_task:
            self._receive_task.cancel()
        
        if self.ws:
            await self.ws.close()
            self.ws = None
        
        self.connected = False
    
    async def send(self, message: str):
        if self.ws and self.connected:
            try:
                await self.ws.send(message)
            except Exception as e:
                Log.warning(
                    f"Error sending message "
                    f"({type(e).__name__}): {repr(e)}"
                    )
                
                self.connected = False
    
    async def _receive_loop(self):
        try:
            while self.running and self.ws:
                try:
                    message = await self.ws.recv()
                    await self.on_message(message)

                except ConnectionClosed:
                    Log.warning("Connection closed by server")
                    self.connected = False
                    break

                except Exception as e:
                    Log.warning(
                        f"Error receiving message "
                        f"({type(e).__name__}): {repr(e)}"
                        )
                    break
                
        except asyncio.CancelledError:
            pass
    
    async def wait_for_disconnect(self):
        while self.running and self.connected:
            await asyncio.sleep(1)