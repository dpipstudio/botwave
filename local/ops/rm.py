from pathlib import Path
from typing import Any

from shared.env import Env
from shared.logger import Log
from shared.ops import CliOp
from shared.security import PathValidator, SecurityError

class RmOp(CliOp):
    """
    The 'rm' command OP. Removes requested files from 
    the upload folder. Also supports globbing ('*.wav', 'morse*', etc).
    """

    name = "rm"
    syntax = "<filename|glob>"

    async def handle(self, target: str = "", is_cmd: bool = False, cmd_parts: list[str] = []):
        if is_cmd:
            target = self.parse(cmd_parts)

            if not target:
                return

        upl_dir = Path(Env.get("UPLOAD_DIR")).resolve()

        try:
            target = PathValidator.sanitize_filename(target)

        except SecurityError:
            Log.error(f"Invalid pattern '{target}'")
            return

        matches = sorted(upl_dir.glob(target))

        # drop anything that resolved outside upl_dir
        # (e.g. via a symlink inside the upload dir)
        safe_matches: list[Path] = []

        for f in matches:
            try:
                resolved = f.resolve()
                resolved.relative_to(upl_dir)
                safe_matches.append(f)

            except ValueError:
                Log.error(f"Skipped '{f.name}': resolves outside upload dir")

        if not safe_matches:
            Log.error(f"No files matching '{target}'")
            return

        count = 0

        for f in safe_matches:
            if f.is_file():
                f.unlink()
                count += 1

        Log.success(f"Removed {count} files from {upl_dir}")


    def parse(self, cmd_parts: list[str]) -> Any:
        if len(cmd_parts) < 1:
            Log.error("Usage: rm <filename|glob>")
            return None

        return cmd_parts[0]


def setup(reg: Any):
    reg.register(RmOp)