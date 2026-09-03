import re
from typing import Any

from shared.logger import Log
from shared.ops import CliOp
from shared.protocol import Commands

class UpdateOp(CliOp):
    """
    The 'update' commands OP. Update the clients software by
    making them use 'bw-update' with eventual provided args
    and then stopping themselves.
    
    If they're running as a service (that bw-autorun can setup),
    they will reconnect with the new version.
    """

    name = "update"
    syntax = "<targets> [version]"
    short_help = "Request client(s) to update and restart"
    long_help = """\
Request the given <targets> to update and restart.
Omit [version] to update to the latest release.
"""
    examples = [
        "update all",
        "update all v1.0.0-oak"
    ]
    env_vars = {}

    async def handle(
            self,
            targets: list[str] = [],
            version: str = "",
            is_cmd: bool = False,
            cmd_parts: list[str] = []
    ):
        if is_cmd:
            targets, version = self.parse(cmd_parts)

            if not targets:
                return

            targets = self.owner.parse_targets(targets)

            if not targets:
                Log.warning("No client(s) found matching the query")
                return

        if version:
            version = version.lower().strip()

            if not re.match(r'^v\d+\.\d+\.\d+', version):
                Log.error(f"Invalid version: '{version}'. Use  a version like 'v1.0.0-oak'")
                return

        Log.update(f"Sending update request to {len(targets)} client(s)...")
        
        results: dict[str, list[str]] = {'updated': [], 'failed': []}

        for client_id in targets:
            if client_id not in self.owner.clients:
                Log.error(f"  {client_id}: Client not found")
                continue

            client = self.owner.clients[client_id]

            try:
                print(version)
                response = await client.proto.send(
                    Commands.UPDATE,
                    version=version,
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

    def parse(self, cmd_parts: list[str]) -> tuple[Any, ...]:
        if len(cmd_parts) < 1:
            Log.error("Usage: update <targets> [version]")
            return (None, None)

        targets = cmd_parts[0]
        version = cmd_parts[1] if len(cmd_parts) > 1 else ""

        return (targets, version)

def setup(reg: Any):
    reg.register(UpdateOp)