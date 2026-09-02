import asyncio
import os
import subprocess
from typing import Any

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
    short_help = "Run a shell command on the host machine"
    long_help = """\
Run a shell <command> on the host machine and print
its output.
"""
    examples = [
        "< df -h"
        "< ls {UPLOAD_DIR}"
    ]
    env_vars = {
        "CMD_INTERPRETER": ("", "The command interpreter to use to execute the given command")
    }

    async def handle(self, command: str = "", is_cmd: bool = False, cmd_parts: list[str] = []):
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

    def run(self, command: str, env: dict[str, str]):
        try:
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, env=env)

            if process.stdout:
                for line in process.stdout:
                    Log.print(line, end='')

            return_code = process.wait()

            if return_code != 0:
                Log.info(f"STDERR (err {return_code}):")

                if process.stderr:
                    for line in process.stderr:
                        Log.print(line, end='')

                Log.error(f"Command failed with return code {return_code}")

        except Exception as e:
            Log.error(f"Error executing shell command: {e}")

    def parse(self, cmd_parts: list[str]) -> Any:
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
    short_help = "Run a shell command and pipe each output line as a BotWave command"
    long_help = """\
Run a shell <command> and pipe each output line as a BotWave command.
"""
    examples = [
        "| echo 'start hello.wav'",
        "| bash /opt/BotWave/scripts/script.sh"
    ]
    env_vars = {
        "CMD_INTERPRETER": ("", "The command interpreter to use to execute the given command")
    }


    async def handle(self, command: str = "", is_cmd: bool = False, cmd_parts: list[str] = []):
        if is_cmd:
            command = self.parse(cmd_parts)
            if not command:
                return

        env = os.environ.copy()
        shell = Env.get("CMD_INTERPRETER")
        if shell:
            command = f"{shell} \"{command}\""

        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[str | Exception | None]  = asyncio.Queue()

        def produce():
            try:
                process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, universal_newlines=True, env=env)

                if process.stdout:
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


    def parse(self, cmd_parts: list[str]) -> Any:
        if len(cmd_parts) < 1:
            Log.error("Usage: | <command>")
            return None

        return ' '.join(cmd_parts)


def setup(reg: Any):
    reg.register(ShellOp)
    reg.register(PipeOp)