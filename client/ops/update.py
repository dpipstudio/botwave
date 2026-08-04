import asyncio
from pathlib import Path
import tempfile

from shared.logger import Log
from shared.ops import GeneralOp
from shared.protocol import Commands
from shared.registry import UpperException

class UpdateOp(GeneralOp):
    commands = {Commands.UPDATE: "update"}

    async def update(self, parsed):
        update_args = parsed['kwargs'].get('args', '')

        Log.update("Update requested by server")
        Log.update(f"Running bw-update {update_args}".strip())

        try:
            proc = await asyncio.create_subprocess_shell(
                f"bw-update {update_args}".strip(),
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

def setup(reg):
    reg.register(UpdateOp)