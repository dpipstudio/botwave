import asyncio
import ssl

from shared.env import Env
from shared.http import BWHTTPFileServer
from shared.logger import Log
from shared.ops import GeneralOp
from shared.registry import UpperException
from shared.socket import BWWebSocketServer
from shared.tls import gen_cert, save_cert

class StartupOp(GeneralOp):
    commands = {"server_startup": "startup"}

    async def startup(self):
        try:
            # tls certs (for https and wss)
            cert_pem, key_pem = gen_cert()
            cert_path, key_path = save_cert(cert_pem, key_pem)
            
            ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ssl_context.load_cert_chain(cert_path, key_path)

            Log.tls("Generated self-signed TLS certificate")

            self.owner.ws_server = BWWebSocketServer(
                ssl_context=ssl_context,
                on_message_callback=self.owner.handle_message,
                on_connect_callback=self.owner.client_connect,
                on_disconnect_callback=self.owner.client_disconnect
            )
            self.owner.http_server = BWHTTPFileServer(ssl_context=ssl_context)
            
            await self.owner.ws_server.start()
            await self.owner.http_server.start()

        except Exception as e:
            Log.error(f"Error starting server: {e}")
            raise UpperException("startup_fail")

def setup(reg):
    reg.register(StartupOp)