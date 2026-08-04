import asyncio
from pathlib import Path
import platform
import ssl
import tempfile

from shared.env import Env
from shared.http import BWHTTPFileClient
from shared.logger import Log
from shared.ops import GeneralOp
from shared.protocol import Commands, PROTOCOL_VERSION
from shared.protomanager import ProtoManager
from shared.registry import UpperException
from shared.socket import BWWebSocketClient
from shared.version import get_release_version

class ConnectOp(GeneralOp):
    commands = {
        "client_connect": "connect",
        Commands.REGISTER_OK: "register_ok"
    }

    async def connect(self):
        Log.client(f"Connecting to wss://{Env.get("SERVER_HOST")}:{Env.get("SERVER_PORT")}...")

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

    async def register_ok(self, parsed):
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

    def create_ssl_context(self):
        # Creates SSL context accepting self-signed certificates
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        return ssl_context

def setup(reg):
    reg.register(ConnectOp)