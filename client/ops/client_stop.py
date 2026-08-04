from shared.logger import Log
from shared.ops import GeneralOp

class ClientStopOp(GeneralOp):
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

def setup(reg):
    reg.register(ClientStopOp)