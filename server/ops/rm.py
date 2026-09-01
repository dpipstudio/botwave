from typing import Any

from shared.logger import Log
from shared.ops import CliOp
from shared.protocol import Commands

class RemoveOp(CliOp):
    """
    The 'rm' command OP. Removes requested files from 
    the target client. Also supports globbing ('*.wav', 'morse*', etc).
    """

    name = "rm"
    syntax = "<targets> <filename|glob>"

    async def handle(
            self,
            targets: list[str] = [],
            file: str = "",
            is_cmd: bool = False,
            cmd_parts: list[str] = []
    ):
        if is_cmd:
            targets, file = self.parse(cmd_parts)

            if not targets:
                return

            targets = self.owner.parse_targets(targets)

            if not targets:
                Log.warning("No client(s) found matching the query")
                return

        results: dict[str, list[str]] = {'deleted': [], 'failed': []}

        Log.info(f"Removing '{file}' from {len(targets)} client(s)...")
                
        for client_id in targets:
            if client_id not in self.owner.clients:
                Log.error(f"  {client_id}: Client not found")
                results["failed"].append(client_id)
                continue
            
            client = self.owner.clients[client_id]

            try:
                response = await client.proto.send(Commands.REMOVE_FILE, filename=file)

                msg = response['kwargs'].get('message', 'File deleted')
                Log.success(f"  {client.get_display_name()}: {msg}")

                results['deleted'].append(client_id)
            
            except TimeoutError:
                Log.error(f"  {client_id}: Response timeout")
                results['failed'].append(client_id)

            except RuntimeError as e:
                Log.error(f"  {client_id}: {e}")
                results['failed'].append(client_id)

        Log.print("")
        Log.info(f"Success: {len(results['deleted'])}, Failure: {len(results['failed'])}")


    def parse(self, cmd_parts: list[str]) -> tuple[Any, ...]:
        if len(cmd_parts) < 2:
            Log.error("Usage: rm <targets> <filename|glob>")
            return (None, None)

        return (cmd_parts[0], cmd_parts[1])

def setup(reg: Any):
    reg.register(RemoveOp)