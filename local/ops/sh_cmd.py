import asyncio
import os
import subprocess

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

        # run in separate thread to avoid blocking the main loop
        await asyncio.to_thread(self.run, command, env)

    def run(self, command, env):
        try:
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, env=env)
            for line in process.stdout:
                Log.print(line, end='')

            return_code = process.wait()

            if return_code != 0:
                Log.info(f"STDERR (err {return_code}):")
                for line in process.stderr:
                    Log.print(line, end='')

                Log.error(f"Command failed with return code {return_code}")

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

        loop = asyncio.get_running_loop()
        queue = asyncio.Queue()

        def produce():
            try:
                process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, universal_newlines=True, env=env)
                for line in process.stdout:
                    line = line.strip()

                    if line:
                        # back to the event loop
                        loop.call_soon_threadsafe(queue.put_nowait, line)

            except Exception as e:
                loop.call_soon_threadsafe(queue.put_nowait, e)

            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)

        thread = asyncio.to_thread(produce)
        task = asyncio.ensure_future(thread)

        while True:
            item = await queue.get()
            if item is None:
                break

            if isinstance(item, Exception):
                Log.error(f"Error executing shell command: {item}")
                break

            await self.owner.cmd_exec(item)

        await task


    def parse(self, cmd_parts):
        if len(cmd_parts) < 1:
            Log.error("Usage: | <command>")
            return None

        return ' '.join(cmd_parts)


def setup(reg):
    reg.register(ShellOp)
    reg.register(PipeOp)