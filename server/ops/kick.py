from shared.logger import Log
from shared.ops import CliOp
from shared.protocol import Commands

class KickOp(CliOp):
    """
    The 'kick' command OP. Kicks the target client by
    sending Commands.KICK and then closing the websocket.

    A client can still join back after being kicked.
    """

    name = "kick"
    syntax = "<targets> [reason]"

    async def handle(
            self,
            targets: list = [],
            reason: str = None,
            is_cmd: bool = False,
            cmd_parts: list = []
    ):
        if is_cmd:
            targets, reason = self.parse(cmd_parts)

            if not targets:
                return

            targets = self.owner.parse_targets(targets)

            if not targets:
                Log.warning("No client(s) found matching the query")
                return

        Log.client(f"Kicking {len(targets)} client(s)...")
        
        results = {'kicked': [], 'failed': []}

        for client_id in targets:
            if client_id not in self.owner.clients:
                Log.error(f"  {client_id}: Client not found")
                results["failed"].append(client_id)
                continue
            
            client = self.owner.clients[client_id]
            
            await client.proto.fire(Commands.KICK, reason=reason)
            
            try:
                await client.websocket.close()

            except:
                pass
            
            del self.owner.clients[client_id]
            
            results["kicked"].append(client_id)
            Log.success(f"  {client.get_display_name()}: Kicked - {reason}")

        Log.print("")
        Log.info(f"Success: {len(results['kicked'])}, Failure: {len(results['failed'])}")


    def parse(self, cmd_parts):
        if len(cmd_parts) < 1:
            Log.error("Usage: kick <targets> [reason]")
            return (None, None)

        targets = cmd_parts[0]
        reason = cmd_parts[1] if len(cmd_parts) > 1 else "Kicked by administrator"

        return (targets, reason)

def setup(reg):
    reg.register(KickOp)