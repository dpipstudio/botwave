import asyncio
import re
import shlex
import tempfile
from pathlib import Path
from typing import Any

from shared.logger import Log
from shared.ops import GeneralOp
from shared.protocol import Commands
from shared.protomanager import ParsedCommand
from shared.registry import UpperException

class UpdateOp(GeneralOp):
    """
    The OP handling Commands.UPDATE. Runs bw-update as a
    subprocess and raises an UpperException() to stop
    the client once it's done.

    If the client is managed by a service such as the one
    that bw-autorun setups, it should automatically restart
    and reconnect with the new version.
    """

    commands = {Commands.UPDATE: "update"}

    async def update(self, parsed: ParsedCommand):
        update_args = parsed['kwargs'].get('args', '').strip()

        # SECURITY: Defense in depth on the client side.
        # Server may construct "--to vX.Y.Z" (or just ""). Reject anything else
        # to prevent shell injection (C-1: RCE as root).
        cmd_args = ["bw-update"]
        if update_args:
            try:
                tokens = shlex.split(update_args)
            except ValueError:
                tokens = update_args.split()

            if len(tokens) != 2 or tokens[0] != "--to":
                Log.error(f"Invalid update args shape: {update_args!r}")
                await self.owner.proto.reply(
                    parsed,
                    Commands.ERROR,
                    message="Invalid update args",
                )
                return

            version = tokens[1]
            if not re.match(r"^v\d+\.\d+\.\d+$", version):
                Log.error(f"Invalid update version: {version!r}")
                await self.owner.proto.reply(
                    parsed,
                    Commands.ERROR,
                    message="Invalid update version",
                )
                return

            cmd_args += ["--to", version]

        Log.update("Update requested by server")
        Log.update(f"Running {' '.join(cmd_args)}")

        try:
            # NO SHELL: pass argv directly. Argument injection impossible.
            proc = await asyncio.create_subprocess_exec(
                *cmd_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            stdout, _ = await proc.communicate()

            if stdout:
                for line in stdout.decode(errors='replace').splitlines():
                    Log.update(line)

            if proc.returncode != 0:
                Log.error(f"bw-update exited with code {proc.returncode}")

                await self.owner.proto.reply(
                    parsed,
                    Commands.ERROR,
                    message=f"Update failed (exit code {proc.returncode})"
                )
                return

        except Exception as e:
            Log.error(f"Update failed: {e}")

            await self.owner.proto.reply(
                parsed,
                Commands.ERROR,
                message=f"Update failed: {e}"
            )
            return

        try:
            Path.touch(Path(tempfile.gettempdir()) / ".bw_updated")

        except Exception:
            pass

        await self.owner.proto.reply(
            parsed,
            Commands.OK,
            message="Update successful, restarting..."
        )

        raise UpperException("update")

def setup(reg: Any):
    reg.register(UpdateOp)