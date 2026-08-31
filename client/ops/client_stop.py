from typing import Any

from shared.logger import Log
from shared.ops import GeneralOp

class ClientStopOp(GeneralOp):
    """
    An internal OP to stop the client. Stops the broadcast
    if any and disconnects from the server.
    """

    commands = {"client_stop": "stop"}

    async def stop(self):
        self.owner.running = False

        if self.owner.broadcasting:
            await self.registry.dispatch("stop_broadcast", silent=True)

        if self.owner.piwave:
            self.owner.piwave.cleanup()

        if self.owner.ws_client:
            await self.owner.ws_client.disconnect()

        self.owner.tips.stop()

        Log.client("Client stopped")

def setup(reg: Any):
    reg.register(ClientStopOp)