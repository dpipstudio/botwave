from pathlib import Path
import ssl
import tempfile

from shared.env import Env
from shared.http import BWHTTPFileServer
from shared.logger import Log
from shared.ops import GeneralOp
from shared.registry import UpperException
from shared.socket import BWWebSocketServer
from shared.tls import gen_cert, save_cert

class StartupOp(GeneralOp):
    """
    The server internal startup sequence.
    
    Creates the TLS certificates and keys (self-signed)
    if they don't exist already (in /tmp/bw_certs/)
    and setups a SSL context with them.

    Then starts the websocket and http server.
    """

    commands = {"server_startup": "startup"}

    async def startup(self):
        try:
            # tls certs (for https and wss)
            bw_certs = Path(tempfile.gettempdir()) / "bw_certs"
            bw_certs.mkdir(exist_ok=True)
            cert_path = bw_certs / "bw.crt"
            key_path = bw_certs / "bw.key"

            try:
                # reuse existing certs if readable
                cert_pem = cert_path.read_text()
                key_pem = key_path.read_text()
                Log.tls("Reusing existing TLS certificate")

            except OSError:
                # missing / unreadable -> regen
                cert_pem, key_pem = gen_cert()

                try:
                    self.save_cert_to(cert_pem, key_pem, cert_path, key_path)

                except OSError:
                    # can't write to the fixed path either, fall back to good old temp files
                    cert_path, key_path = save_cert(cert_pem, key_pem)

                finally:
                    Log.tls("Generated self-signed TLS certificate")

            ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ssl_context.load_cert_chain(cert_path, key_path)


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

    def save_cert_to(self, cert_pem: str, key_pem: str, cert_path: Path, key_path: Path):
        cert_path.write_text(cert_pem)
        key_path.write_text(key_pem)

def setup(reg):
    reg.register(StartupOp)