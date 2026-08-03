import os

from shared.env import Env
from shared.logger import Log
from shared.ops import CliOp

class GetOp(CliOp):
    name = "get"
    syntax = "<keys|*>"

    async def handle(self, keys: list = None, is_cmd: bool = False, cmd_parts: list = []):
        if is_cmd:
            keys = self.parse(cmd_parts)

            if not keys:
                return

        if "*" in keys:
            keys = list(os.environ.copy().keys())

        for key in keys:
            key = key.upper()
            value, immutable = Env.get(key, get_immutability=True)

            if not value:
                Log.environ(f"'{key}' doesn't exit in the current environment")
                continue

            Log.print("", style="rgb(224,107,61)", icon="ENV", end="")
            Log.print(f"({key})", style="bright_blue", end=" ")
            Log.print(value, style="orange" if immutable else "white")


    def parse(self, cmd_parts):
        if len(cmd_parts) < 1: 
            Log.error("Usage: get <keys|*>")
            return None

        return cmd_parts

class SetOp(CliOp):
    name = "set"
    syntax = "<key> <value> [immutable]"

    async def handle(self, key: str = None, value: str = None, immutable: bool = False, is_cmd: bool = False, cmd_parts: list = []):
        if is_cmd:
            key, value, immutable = self.parse(cmd_parts)

            if not key:
                return

        try:
            Env.set(key, value, immutable)

        except ValueError as e:
            Log.environ(str(e))
            return
        
        await self.registry.dispatch("get", keys=[key])


    def parse(self, cmd_parts):
        if len(cmd_parts) < 2:
            Log.error("Usage: set <key> <value> [immutable]")
            return (None, None, None)

        key = cmd_parts[0]
        value = cmd_parts[1]
        immutable = cmd_parts[2].lower() == "true" if len(cmd_parts) > 2 else False

        return (key, value, immutable)

def setup(reg):
    reg.register(GetOp)
    reg.register(SetOp)