from typing import Any

from shared.logger import Log
from shared.ops import CliOp
from shared.protocol import Commands

class StopOp(CliOp):
    """
    The 'stop' command OP. Stops eventual broadcasts on clients.
    Also stops the ALSA recorder.
    """

    name = "stop"
    syntax = "<targets>"
    short_help = "Stop broadcasting on client(s)"
    long_help = """\
Stop the current broadcast on the given <targets>, and
stop the local ALSA recorder.
"""
    examples = [
        "stop all"
    ]
    env_vars = {}

    async def handle(
        self,
        targets: list[str] = [],
        is_cmd: bool = False,
        cmd_parts: list[str] = []
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

        results: dict[str, list[str]] = {'stopped': [], 'failed': []}
        
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
                results['failed'].append(client_id)

            except RuntimeError as e:
                err = str(e)

                Log.error(f"  {client.get_display_name()}: {err}")
                results['failed'].append(client_id)

        Log.print("")        
        Log.info(f"Success: {len(results['stopped'])}, Failure: {len(results['failed'])}")

        self.owner.alsa.stop()
        await self.registry.dispatch("handlers_onstop")

        
    def parse(self, cmd_parts: list[str]) -> Any:
        if len(cmd_parts) < 1:
            Log.error("Usage: stop <targets>")
            return None

        return cmd_parts[0]

def setup(reg: Any):
    reg.register(StopOp)