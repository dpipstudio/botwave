import json
from typing import Any

from shared.logger import Log
from shared.ops import CliOp
from shared.protocol import Commands

class ListFilesOp(CliOp):
    """
    The 'lf' command OP. Prints the files that the target
    has in its upload folder. Currently prints the file's name and size.
    """

    name = "lf"
    syntax = "<targets>"
    short_help = "List broadcastable files on client(s)"
    long_help = """\
List the files present in the upload folder of the given
<targets>.
"""
    examples = [
        "lf all"
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

        results: dict[str, list[str]] = {'fetched': [], 'failed': []}

        for client_id in targets:
            if client_id not in self.owner.clients:
                Log.error(f"  {client_id}: Client not found")
                results['failed'].append(client_id)
                continue

            client = self.owner.clients[client_id]

            try:
                response = await client.proto.send(Commands.LIST_FILES, timeout=10.0)
                files = json.loads(response['kwargs'].get('files', '[]'))

                Log.success(f"  {client.get_display_name()}: {len(files)} file(s)")

                for f in files:
                    size = f.get('size', 0)
                    if size < 1024: size_str = f"{size} B"
                    elif size < 1024 * 1024: size_str = f"{size / 1024:.1f} KB"
                    else: size_str = f"{size / (1024 * 1024):.1f} MB"
                    Log.print(f"    {f['name']} ({size_str})", 'white')

                results['fetched'].append(client_id)

            except TimeoutError:
                Log.error(f"  {client_id}: Response timeout")
                results['failed'].append(client_id)

            except RuntimeError as e:
                Log.error(f"  {client_id}: {e}")
                results['failed'].append(client_id)

        Log.print("")
        Log.info(f"Success: {len(results['fetched'])}, Failure: {len(results['failed'])}")


    def parse(self, cmd_parts: list[str]) -> Any:
        if len(cmd_parts) < 1:
            Log.error("Usage: lf <targets>")
            return None

        return cmd_parts[0]

def setup(reg: Any):
    reg.register(ListFilesOp)