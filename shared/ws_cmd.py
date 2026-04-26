import asyncio
import threading
from typing import Callable, Set, Optional
import websockets

from shared.env import Env
from shared.logger import Log


class WSCMDH: # WebSocket Command Handler
    
    def __init__(self, command_executor: Callable,
                 onwsjoin_callback: Optional[Callable] = None,
                 onwsleave_callback: Optional[Callable] = None):
        
        #onwsjoin and leave are for the handlers
        self.command_executor = command_executor
        self.onwsjoin_callback = onwsjoin_callback
        self.onwsleave_callback = onwsleave_callback
        self.ws_clients: Set = set()
        self.ws_loop: Optional[asyncio.AbstractEventLoop] = None
        self.command_history = []
        self.history_index = 0
        
    @property
    def host(self):
        return Env.get("HOST")

    @property
    def port(self):
        return Env.get_int("REMOTE_CMD_PORT")
    
    @property
    def passkey(self):
        return Env.get("PASSKEY")
    
    @property
    def allow_commands(self):
        return Env.get_bool("ALLOW_REMOTE_BLOCKED_COMMANDS_I_KNOW_WHAT_IM_DOING")
    
    @property
    def blocked_commands(self):
        blocked_env = Env.get("REMOTE_BLOCKED_CMD")
        if blocked_env:
            return [cmd for cmd in blocked_env.split(",") if cmd.strip()]

        return ['get', 'set', '<', '|'] # defaults

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
            Log.server(f"Remote CLI server started on ws://{self.host}:{self.port}")
            await asyncio.Future()  # run forever
    
    async def _handle_client(self, websocket):
        try:
            # auth
            ip = websocket.remote_address[0] or "unknown"

            Log.client(f"Remote CLI connection attempt from {ip}")

            if self.passkey:
                await websocket.send("Password: ")
                password = await asyncio.wait_for(websocket.recv(), timeout=Env.get_int("REMOTE_CMD_PWD_TIMEOUT", 60))
                
                if password.strip() != self.passkey:
                    Log.auth(f"{ip} failed to authenticate")

                    await websocket.send("Authentication failed.")
                    await websocket.close()
                    return
                
            Log.auth(f"{ip} connected")
            await websocket.send("OK.")
            await websocket.send(Env.get("REMOTE_CMD_WELCOME", ""))

            self.ws_clients.add(websocket)
            Log.ws_clients = self.ws_clients
            
            if self.onwsjoin_callback:
                self.onwsjoin_callback()
            
            async for message in websocket:
                Log.print(f"{message}", 'bright_green', icon=ip)
                self._inject_command(message, websocket)
                
        except asyncio.TimeoutError:
            await websocket.send("Authentication timeout.")
            await websocket.close()
        finally:
            self.ws_clients.discard(websocket)
            Log.ws_clients = self.ws_clients
            
            if self.onwsleave_callback:
                self.onwsleave_callback()

    async def _close_client(self, websocket):
        await websocket.close()
    
    def _inject_command(self, message: str, websocket):
        def execute():

            self.command_history.append(message)
            self.history_index = len(self.command_history)
            
            cmd_parts = message.strip().split()
            if cmd_parts:
                command = cmd_parts[0].lower()

                if command == '#':
                    return

                if command == 'exit':
                    asyncio.run_coroutine_threadsafe(
                        self._close_client(websocket),
                        self.ws_loop
                    )
                    return

                if command in self.blocked_commands and not self.allow_commands:
                    Log.warning(f"Hmmm, you can't do that. ;)")
                    return

            self.command_executor(message, interpolate=False)
        
        self.ws_loop.call_soon_threadsafe(
            lambda: self.ws_loop.run_in_executor(None, execute)
        )