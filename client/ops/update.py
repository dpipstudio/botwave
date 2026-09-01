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
        version = parsed['kwargs'].get('version', '').strip()

        command = ["bw-update"]

        if version:
            try:
                tokens = shlex.split(version)

            except ValueError:
                tokens = version.split()

            if len(tokens) != 1 or not re.match(r'^v\d+\.\d+\.\d+', tokens[0]):
                Log.error(f"Invalid update version: {version}")

                await self.owner.proto.reply(
                    parsed,
                    Commands.ERROR,
                    message="Invalid update version"
                )
                return

            command += [version]

        Log.update("Update requested by server")
        Log.update(f"Running {' '.join(command)}".strip())

        try:
            proc = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
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