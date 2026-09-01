from pathlib import Path
from typing import Any

from shared.env import Env
from shared.logger import Log
from shared.ops import GeneralOp
from shared.protocol import Commands, ParsedCommand
from shared.security import PathValidator, SecurityError

class RemoveOp(GeneralOp):
    """
    The OP handling Commands.REMOVE_FIlE. Removes the
    requested file(s) from the upload dir. Also supports
    globbing (so *.wav, morse_*, etc work)
    """

    commands = {Commands.REMOVE_FILE: "rm"}

    async def rm(self, parsed: ParsedCommand):
        filename = parsed['kwargs'].get("filename")

        if not filename:
            await self.owner.proto.reply(
                parsed,
                Commands.ERROR,
                message="Missing filename"
            )
            return

        upl_dir = Path(Env.get("UPLOAD_DIR")).resolve()

        try:
            target = PathValidator.sanitize_filename(filename)

        except SecurityError as e:
            Log.error(f"Security violation in remove: {e}")

            await self.owner.proto.reply(
                parsed,
                Commands.ERROR,
                message="Provided filename raised a security violation"
            )
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

            await self.owner.proto.reply(
                parsed,
                Commands.ERROR,
                message="File not found"
            )
            return

        count = 0

        for f in safe_matches:
            if f.is_file():
                f.unlink()
                count += 1

        Log.success(f"Removed {count} files from {upl_dir}")

        await self.owner.proto.reply(
            parsed,
            Commands.OK,
            message=f"Removed {filename} ({count} files)"
        )


def setup(reg: Any):
    reg.register(RemoveOp)