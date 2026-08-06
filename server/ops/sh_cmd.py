import asyncio
import os

from shared.env import Env
from shared.logger import Log
from shared.ops import CliOp

class ShellOp(CliOp):
    """
    The '<' command OP. Executes a shell command locally and streams
    stdout/stderr back to the console.
    """

    name = "<"
    syntax = "<command>"

    async def handle(self, command: str = None, is_cmd: bool = False, cmd_parts: list = []):
        if is_cmd:
            command = self.parse(cmd_parts)
            if not command:
                return

        env = os.environ.copy()
        shell = Env.get("CMD_INTERPRETER")
        if shell:
            command = f"{shell} \"{command}\""

        await self.run(command, env)

    async def run(self, command, env):
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )

            try:
                async def read_stream(stream, is_stderr=False):
                    while True:
                        line = await stream.readline()
                        if not line:
                            break

                        if is_stderr:
                            Log.print(line.decode('utf-8'), style="red", end='')

                        else:
                            Log.print(line.decode('utf-8'), end='')

                await asyncio.wait_for(
                    asyncio.gather(
                        read_stream(process.stdout),
                        read_stream(process.stderr, is_stderr=True)
                    ),
                    timeout=30.0
                )

            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                Log.error("Command execution timeout")

        except Exception as e:
            Log.error(f"Error executing shell command: {e}")

    def parse(self, cmd_parts):
        if len(cmd_parts) < 1:
            Log.error("Usage: < <command>")
            return None

        return ' '.join(cmd_parts)

class PipeOp(CliOp):
    """
    The '|' command OP. Executes a shell command locally and dispatches
    each line of its output as a separate command.
    """
    
    name = "|"
    syntax = "<command>"

    async def handle(self, command: str = None, is_cmd: bool = False, cmd_parts: list = []):
        if is_cmd:
            command = self.parse(cmd_parts)
            if not command:
                return

        env = os.environ.copy()
        shell = Env.get("CMD_INTERPRETER")
        if shell:
            command = f"{shell} \"{command}\""

        await self.run(command, env)

    async def run(self, command, env):
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )

            tasks = []

            async for line in process.stdout:
                line = line.decode('utf-8').strip()
                if line:
                    tasks.append(
                        asyncio.create_task(
                            self.owner.cmd_exec(line)
                        )
                    )

            # wait for the subprocess itself to finish too
            await process.wait()

            # wait for every scheduled command to actually complete before returning
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

        except Exception as e:
            Log.error(f"Error executing pipe command: {e}")

    def parse(self, cmd_parts):
        if len(cmd_parts) < 1:
            Log.error("Usage: | <command>")
            return None

        return ' '.join(cmd_parts)


def setup(reg):
    reg.register(ShellOp)
    reg.register(PipeOp)