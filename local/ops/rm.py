from pathlib import Path

from shared.env import Env
from shared.logger import Log
from shared.ops import CliOp
from shared.security import PathValidator, SecurityError

class RmOp(CliOp):
    name = "rm"
    syntax = "<filename|glob>"

    async def handle(self, target: str = None, is_cmd: bool = False, cmd_parts: str = None):
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

        if target == "all":
            Log.warning("'rm all' is deprecated, use 'rm *' instead. This will be removed in a future release.")
            target = "*.wav" # old behavior only deleted .wav files


        matches = sorted(upl_dir.glob(target))

        # drop anything that resolved outside upl_dir
        # (e.g. via a symlink inside the upload dir)
        safe_matches = []

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


    def parse(self, cmd_parts):
        if len(cmd_parts) < 1:
            Log.error("Usage: rm <filename|glob>")
            return None

        return cmd_parts[0]


def setup(reg):
    reg.register(RmOp)