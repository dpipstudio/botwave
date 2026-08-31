import asyncio
import threading
import re
from typing import Awaitable, Callable
from websockets.exceptions import ConnectionClosed
from websockets.asyncio.server import ServerConnection, serve


from shared.env import Env
from shared.logger import Log
from shared.registry import Registry

class WSCMDH: # WebSocket Command Handler
    
    def __init__(self, command_executor: Callable[..., Awaitable[None]], registry: Registry):
        
        self.command_executor = command_executor
        self.registry = registry
        self.ws_clients: set[ServerConnection] = set()
        self.ws_loop: asyncio.AbstractEventLoop | None = None
        
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
        async with serve(self._handle_client, self.host, self.port):
            Log.server(f"Remote CLI server started on ws://{self.host}:{self.port}")
            await asyncio.Future()  # run forever
    
    async def _handle_client(self, websocket: ServerConnection):
        ip = websocket.remote_address[0] or "unknown"

        try:
            # auth
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
            
            await self.registry.dispatch("handlers_onwsjoin", context={"REMOTE_CLIENT_IP": ip})
            
            try:
                async for message in websocket:
                    await self._inject_command(str(message), websocket, ip)

            except ConnectionClosed:
                pass  # exit
                
        except asyncio.TimeoutError:
            await websocket.send("Authentication timeout.")
            await websocket.close()

        finally:
            Log.client(f"Remote CLI disconnected: {ip}")
            self.ws_clients.discard(websocket)
            Log.ws_clients = self.ws_clients
            
            await self.registry.dispatch("handlers_onwsleave", context={"REMOTE_CLIENT_IP": ip})

    async def _close_client(self, websocket: ServerConnection):
        await websocket.close()
        await websocket.wait_closed()
    
    async def _inject_command(self, message: str, websocket: ServerConnection, ip: str):
        cmd = re.sub(r'\s*transaction_id=[^\s]+', '', message).strip()
        Log.print(cmd, 'bright_green', icon=ip)
        
        cmd_parts = message.strip().split()
        if cmd_parts:
            command = cmd_parts[0].lower()

            if command == '#':
                return

            if command == 'exit':
                await self._close_client(websocket)
                return

            if command in self.blocked_commands and not self.allow_commands:
                Log.warning(f"Hmmm, you can't do that. ;)")
                return

        Log.set_remote_cmd(websocket) # Output of the exec cmd will eventually be isolated
        await self.command_executor(message, interpolate=Env.get_bool("INTERPOLATE_REMOTE"))
        Log.clear_remote_cmd()