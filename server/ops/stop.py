from datetime import datetime, timezone

from shared.env import Env
from shared.logger import Log
from shared.ops import CliOp
from shared.protocol import Commands

class StopOp(CliOp):
    name = "stop"
    syntax = "<targets>"

    async def handle(
        self,
        targets: list = [],
        is_cmd: bool = False,
        cmd_parts: list = []
    ):
        if is_cmd:
            targets = self.parse(cmd_parts)

            if not targets:
                return

            targets = self.owner.parse_targets(targets)

            if not targets:
                Log.warning("No client(s) found matching the query")
                return

            self.owner.queue.manual_pause()

        results = {'stopped': [], 'failed': []}
        
        for client_id in targets:
            if client_id not in self.owner.clients:
                Log.error(f"  {client_id}: Client not found")
                results['failed'].append(client_id)
                continue

            
            client = self.owner.clients[client_id]
            
            try: 
                response = await client.proto.send(Commands.STOP)

                Log.success(f"  {client.get_display_name()}: {response['kwargs'].get('message', 'Broadcast stopped')}")
                results['stopped'].append(client_id)

            except TimeoutError:
                Log.error(f"  {client.get_display_name()}: Response timeout")
                results['failed'].append((client_id, 'timeout'))

            except RuntimeError as e:
                err = str(e)

                Log.error(f"  {client.get_display_name()}: {err}")
                results['failed'].append((client_id, err))

        Log.print("")        
        Log.info(f"Success: {len(results['stopped'])}, Failure: {len(results['failed'])}")

        self.owner.alsa.stop()
        await self.registry.dispatch("handlers_onstop")

        
    def parse(self, cmd_parts):
        if len(cmd_parts) < 1:
            Log.error("Usage: stop <targets>")
            return None

        return cmd_parts[0]

def setup(reg):
    reg.register(StopOp)