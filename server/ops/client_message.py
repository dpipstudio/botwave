from shared.logger import Log
from shared.ops import GeneralOp
from shared.protocol import Commands

class ClientMsgOp(GeneralOp):
    commands = {
        Commands.OK: "success",
        Commands.ERROR: "error",
        Commands.END: "end"
    }

    async def success(self, client_id, parsed, websocket):
        msg = parsed['kwargs'].get('message', 'OK')
        Log.success(f"{self.owner.clients[client_id].get_display_name()}: {msg}")


    async def error(self, client_id, parsed, websocket):
        msg = parsed['kwargs'].get('message', 'Error')
        Log.error(f"{self.owner.clients[client_id].get_display_name()}: {msg}")


    async def end(self, client_id, parsed, websocket):
        kwargs = parsed['kwargs']

        filename = kwargs.get('filename', 'unknown')
        msg = kwargs.get('message')

        if msg:
            Log.error(f"{self.owner.clients[client_id].get_display_name()}: {msg}")

        else:
            Log.broadcast(f"{self.owner.clients[client_id].get_display_name()}: Finished broadcasting {filename}")

        self.owner.queue.on_broadcast_ended(client_id)
        return

def setup(reg):
    reg.register(ClientMsgOp)