import asyncio
import json
import threading
from typing import Callable, Set, Optional
import websockets
from shared.logger import Log


class WSCMDH: # WebSocket Command Handler
    
    def __init__(self, host: str, port: int, passkey: Optional[str], 
                 command_executor: Callable, is_server: bool = False,
                 onwsjoin_callback: Optional[Callable] = None,
                 onwsleave_callback: Optional[Callable] = None):
        
        #onwsjoin and leave are for the handlers

        self.host = host
        self.port = port
        self.passkey = passkey
        self.command_executor = command_executor
        self.is_server = is_server
        self.onwsjoin_callback = onwsjoin_callback
        self.onwsleave_callback = onwsleave_callback
        self.ws_clients: Set = set()
        self.ws_loop: Optional[asyncio.AbstractEventLoop] = None
        self.command_history = []
        self.history_index = 0
        
        self.blocked_commands = ['<', 'exit'] # only for server
    
    def start(self):
        
        # starts in a background thread
        threading.Thread(target=self._run_server, daemon=True).start()
    
    def _run_server(self):
        
        # main loop
        self.ws_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.ws_loop)
        Log.ws_loop = self.ws_loop
        self.ws_loop.run_until_complete(self._serve())
    
    async def _serve(self):
        async with websockets.serve(self._handle_client, self.host, self.port):
            Log.server(f"WebSocket server started on {self.host}:{self.port}")
            await asyncio.Future()  # run forever
    
    async def _handle_client(self, websocket):
        try:
            # auth
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
            Log.ws_clients = self.ws_clients
            
            if self.onwsjoin_callback:
                self.onwsjoin_callback()
            
            async for message in websocket:
                Log.client(f"WebSocket CMD: {message}")
                self._inject_command(message)
                
        except asyncio.TimeoutError:
            await websocket.send(json.dumps({"type": "error", "message": "Authentication timeout"}))
            await websocket.close()
        finally:
            self.ws_clients.discard(websocket)
            Log.ws_clients = self.ws_clients
            
            if self.onwsleave_callback:
                self.onwsleave_callback()
    
    def _inject_command(self, message: str):
        def execute():

            self.command_history.append(message)
            self.history_index = len(self.command_history)
            
            # blocked cmds
            if self.is_server:
                cmd_parts = message.strip().split()
                if cmd_parts:
                    command = cmd_parts[0].lower()
                    if command in self.blocked_commands:
                        Log.warning(f"Hmmm, you can't do that. ;)")
                        return
                    
                    if command == '#':
                        return

            self.command_executor(message)
        
        asyncio.get_event_loop().call_soon_threadsafe(execute)