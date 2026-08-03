import os
import subprocess

from shared.env import Env
from shared.logger import Log
from shared.ops import CliOp

class ShellOp(CliOp):
    name = "<"
    syntax = "<command>"

    async def handle(self, command: str = None, is_cmd: bool = False, cmd_parts: list = []):
        if is_cmd:
            command = self.parse(cmd_parts)

            if not command:
                return

        env = os.environ.copy()

        try:
            shell = Env.get("CMD_INTERPRETER")
            if shell:
                command = f"{shell} \"{command}\""

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
    name = "|"
    syntax = "<command>"

    async def handle(self, command: str = None, is_cmd: bool = False, cmd_parts: list = []):
        if is_cmd:
            command = self.parse(cmd_parts)

            if not command:
                return

        env = os.environ.copy()

        try:
            shell = Env.get("CMD_INTERPRETER")
            if shell:
                command = f"{shell} \"{command}\""

            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, universal_newlines=True, env=env)

            for line in process.stdout:
                line = line.strip()
                if line:
                    await self.owner.cmd_exec(line)

        except Exception as e:
            Log.error(f"Error executing shell command: {e}")


    def parse(self, cmd_parts):
        if len(cmd_parts) < 1:
            Log.error("Usage: | <command>")
            return None

        return ' '.join(cmd_parts)


def setup(reg):
    reg.register(ShellOp)
    reg.register(PipeOp)