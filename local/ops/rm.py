from pathlib import Path

from shared.env import Env
from shared.logger import Log
from shared.ops import CliOp

class RmOp(CliOp):
    name = "rm"
    syntax = "<filename|glob>"

    async def handle(self, target: str = None, is_cmd: bool = False, cmd_parts: str = None):
        if is_cmd:
            target = self.parse(cmd_parts)

            if not target:
                return

        upl_dir = Path(Env.get("UPLOAD_DIR"))
        matches = sorted(upl_dir.glob(target))

        if not matches:
            Log.error(f"No files matching '{target}'")
            return

        count = 0

        for f in matches:
            if f.is_file():
                f.unlink()
                count += 1

        Log.success(f"Removed {count} files from {upl_dir}")


    def parse(self, cmd_parts):
        if len(cmd_parts) < 1:
            Log.error("Usage: rm <filename|glob>")
            return None

        return cmd_parts[0]


def setup(reg):
    reg.register(RmOp)