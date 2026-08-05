import re

from shared.logger import Log
from shared.ops import CliOp
from shared.protocol import Commands

class UpdateOp(CliOp):
    name = "update"
    syntax = "<targets> [version]"

    async def handle(
            self,
            targets: list = [],
            version: str = None,
            is_cmd: bool = False,
            cmd_parts: list = []
    ):
        if is_cmd:
            targets, version = self.parse(cmd_parts)

            if not targets:
                return

            targets = self.owner.parse_targets(targets)

            if not targets:
                Log.warning("No client(s) found matching the query")
                return

        args = ''

        if version:
            version = version.lower().strip()

            if re.match(r'^v\d+\.\d+\.\d+', version):
                args = f"--to {version}"

            else:
                Log.error(f"Invalid version: '{version}'. Use  a version like 'v1.0.0-oak'")
                return

        Log.update(f"Sending update request to {len(targets)} client(s)...")
        
        results = {'updated': [], 'failed': []}

        for client_id in targets:
            if client_id not in self.owner.clients:
                Log.error(f"  {client_id}: Client not found")
                continue

            client = self.owner.clients[client_id]

            try:
                response = await client.proto.send(
                    Commands.UPDATE,
                    args=args,
                    timeout=300.0
                )
                results['updated'].append(client_id)
                Log.success(f"  {client.get_display_name()}: {response['kwargs'].get('message', 'OK')}")

            except TimeoutError:
                results['failed'].append(client_id)
                Log.error(f"  {client.get_display_name()}: Response timeout")

            except RuntimeError as e:
                results['failed'].append(client_id)
                Log.error(f"  {client.get_display_name()}: {e}")

        Log.print("")
        Log.info(f"Success: {len(results['updated'])}, Failure: {len(results['failed'])}")

    def parse(self, cmd_parts):
        if len(cmd_parts) < 1:
            Log.error("Usage: update <targets> [version]")
            return (None, None)

        targets = cmd_parts[0]
        reason = cmd_parts[1] if len(cmd_parts) > 1 else None

        return (targets, reason)

def setup(reg):
    reg.register(UpdateOp)