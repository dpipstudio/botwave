import asyncio
import platform
import ssl
import tempfile
from pathlib import Path
from typing import Any

from shared.env import Env
from shared.http import BWHTTPFileClient
from shared.logger import Log
from shared.ops import GeneralOp
from shared.protocol import Commands, PROTOCOL_VERSION
from shared.protomanager import ParsedCommand, ProtoManager
from shared.registry import UpperException
from shared.socket import BWWebSocketClient
from shared.version import get_release_version

class ConnectOp(GeneralOp):
    """
    An internal OP used to connect to the server 
    (wss:/SERVER_HOST:SERVER_PORT). It handles the 
    custom SSL context, creates the ws_client and
    http_client and connects to the server.

    It then handles the expected registration flow:
      1. Send Commands.REGISTER with machine info
      2. Send Commands.AUTH if we got a passkey
      3. Send Commands.VER with our current proto ver

    Then it handles different server responses such as:
      - Commands.REGISTER_OK: we're successfully connected
        and registered
      - Commands.AUTH_FAILED: missing or wrong passkey
      - Commands.VERSION_MISMATCH: our protocol version
        is too different from the server's one

    Raises an UpperException() on fails
    """

    commands = {
        "client_connect": "connect",
        Commands.REGISTER_OK: "register_ok",
        Commands.AUTH_FAILED: "auth_failed",
        Commands.VERSION_MISMATCH: "ver_mismatch"
    }

    async def connect(self):
        Log.client(f"Connecting to wss://{Env.get('SERVER_HOST')}:{Env.get('SERVER_PORT')}...")

        ssl_context = self.create_ssl_context()

        self.owner.ws_client = BWWebSocketClient(
            ssl_context=ssl_context,
            on_message_callback=self.owner.handle_message
        )

        self.owner.http_client = BWHTTPFileClient(ssl_context=ssl_context)
        self.owner.proto = ProtoManager(send_fn=self.owner.ws_client.send)

        if not await self.owner.ws_client.connect():
            raise UpperException("fail_connect")

        Log.success("WebSocket connected, registering...")

        machine_info = {
            "hostname": platform.node(),
            "machine": platform.machine(),
            "system": platform.system(),
            "release": platform.release()
        }

        await self.owner.proto.fire(
            Commands.REGISTER,
            hostname=machine_info['hostname'],
            machine=machine_info['machine'],
            system=machine_info['system'],
            release=machine_info['release']
        )

        passkey = Env.get("PASSKEY")

        if passkey:
            await self.owner.proto.fire(Commands.AUTH, passkey)

        await self.owner.proto.fire(Commands.VER, PROTOCOL_VERSION)

        for _ in range(50):  # wait up to 5s
            if self.owner.registered:
                return
            
            await asyncio.sleep(0.1)

        Log.error("Registration timeout")
        raise UpperException("reg_timeout")

    def create_ssl_context(self):
        # Creates SSL context accepting self-signed certificates
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        return ssl_context

    async def register_ok(self, parsed: ParsedCommand):
        kwargs = parsed['kwargs']

        self.owner.client_id = kwargs.get('client_id', 'unknown')
        self.owner.registered = True

        Log.success(f"Registered as: {self.owner.client_id}")

        update_flag = Path(tempfile.gettempdir()) / ".bw_updated"

        if update_flag.is_file():
            new_version = get_release_version()

            if new_version:
                message = f"BotWave updated to {new_version}"

            else:
                message = "BotWave updated successfully"

            await self.owner.proto.fire(Commands.OK, message=message)
            update_flag.unlink()

    async def auth_failed(self, parsed: ParsedCommand):
        kwargs = parsed['kwargs']

        self.owner.registered = True # to exit the wait-for-register loop
        reason = kwargs.get('message', 'Invalid passkey')
        Log.error(f"Authentication failed: {reason}")

        raise UpperException("auth_failed")

    async def ver_mismatch(self, parsed: ParsedCommand):
        kwargs = parsed['kwargs']

        self.owner.registered = True
        server_ver = kwargs.get('server_version', 'unknown')
        Log.error(f"Protocol version mismatch! Server: {server_ver}, Client: {PROTOCOL_VERSION}")

        raise UpperException("version_mismatch")

def setup(reg: Any):
    reg.register(ConnectOp)