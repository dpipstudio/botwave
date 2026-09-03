import fnmatch
import os
from typing import Any

from shared.env import Env
from shared.logger import Log
from shared.ops import CliOp

class GetOp(CliOp):
    """
    The 'get' command OP. Prints the given environment vars values.

    Immutable (variables wrapped in immutable()) vars are printed in orange
    while non-immutable ones are printed in white.

    Supports multiple keys, separated by spaces (get PORT FPORT)
    and globbing ('get *PORT' -> 'get PORT FPORT') 
    """

    name = "get"
    syntax = "<keys|glob>"
    short_help = "Get one or more environment variables"
    long_help = """\
Get one or more environment variables.
You can specify multiple <keys> at once, or use globbing
to match a large number of keys.
Immutable variables are shown in orange.
"""
    examples = [
        "get PORT",
        "get PORT HOST FPORT",
        "get *PORT",
        "get *"
    ]
    env_vars = {}

    async def handle(self, keys: list[str] = [], is_cmd: bool = False, cmd_parts: list[str] = []):
        if is_cmd:
            keys = self.parse(cmd_parts)

            if not keys:
                return

        env_keys = list(os.environ.keys())
        expanded_keys: list[str] = []

        for pattern in keys:
            pattern = pattern.upper()
            matches = fnmatch.filter(env_keys, pattern)

            if matches:
                expanded_keys.extend(matches)

            else:
                expanded_keys.append(pattern)

        # remove duplicates
        keys = list(dict.fromkeys(expanded_keys))

        for key in keys:
            key = key.upper()
            value, immutable = Env.get(key, get_immutability=True)

            if not value:
                Log.environ(f"'{key}' doesn't exit in the current environment")
                continue

            Log.print("", style="rgb(224,107,61)", icon="ENV", end="")
            Log.print(f"({key})", style="bright_blue", end=" ")
            Log.print(value, style="orange" if immutable else "white")

    def parse(self, cmd_parts: list[str]) -> Any:
        if len(cmd_parts) < 1: 
            Log.error("Usage: get <keys|glob>")
            return None

        return cmd_parts

class SetOp(CliOp):
    """
    The 'set' command OP. Helper to set a variable to a specific value.

    Can only set a single variable at a time, and will fail
    if we try to set an immutable variable. However, this can
    be bypassed by setting the 'immutable' argument to true:

    set PORT 8888 -> fail
    set PORT 8888 true -> succeeds
    """

    name = "set"
    syntax = "<key> <value> [immutable]"
    short_help = "Set an environment variable"
    long_help = """\
Set an environment variable (<key>) to <value>.
If [immutable] is 'true', the value cannot be changed without
re-setting it as immutable. Editing those values is not recommended.
"""
    examples = [
        "set PROMPT_TEXT \"._.\"",
        "set PASSKEY mykey true"
    ]
    env_vars = {}

    async def handle(
        self,
        key: str = "",
        value: str = "",
        immutable: bool = False,
        is_cmd: bool = False,
        cmd_parts: list[str] = []
    ):
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


    def parse(self, cmd_parts: list[str]) -> tuple[Any, ...]:
        if len(cmd_parts) < 2:
            Log.error("Usage: set <key> <value> [immutable]")
            return (None, None, None)

        key = cmd_parts[0]
        value = cmd_parts[1]
        immutable = cmd_parts[2].lower() == "true" if len(cmd_parts) > 2 else False

        return (key, value, immutable)

def setup(reg: Any):
    reg.register(GetOp)
    reg.register(SetOp)