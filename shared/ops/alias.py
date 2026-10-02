import shlex
from typing import Any

from shared.logger import Log
from shared.ops import CliOp

class AliasCmdOp(CliOp):
    """
    The 'alias' command OP. Manages and list
    command aliases.
    """

    name = "alias"
    syntax = "<name> [value]"
    short_help = "Manage command aliases"
    long_help = """\
"""
    examples = [
        "alias smf",
        "alias smf \"start myfile.wav\"",
    ]
    env_vars = {}

    async def handle(self, name: str, value: str = "", is_cmd: bool = False, cmd_parts: list[str] = []):
        if is_cmd:
            name, value = self.parse(cmd_parts)

            if not name:
                return

        if value:
            self.set_alias(name, value)
            return
        
        value = self.owner.aliases.get(name)

        if not value:
            Log.warning(f"No alias with the name '{name}' was found.")
            Log.warning(f"Create a new one with 'alias {name} \"command\"'")
            return

        Log.print(f"The alias '{name}' represents '{value}'")

    def set_alias(self, name: str, value: str):
        command = shlex.split(value)[0]

        if not self.registry.operations.get(command):
            Log.error(f"'{value}' wants to execute '{command}' that is not a registered command.")
            Log.error("Please only register aliases for known commands")
            return

        self.owner.aliases.set(name, value)
        Log.success(f"Set alias '{name}' to represent '{value}'")

    def parse(self, cmd_parts: list[str]) -> tuple[Any, ...]:
        if len(cmd_parts) < 1:
            Log.error("Usage: alias <name> [value]")
            return (None, None)

        name = cmd_parts[0]
        value = cmd_parts[1] if len(cmd_parts) > 1 else ""

        return (name, value)

def setup(reg: Any):
    reg.register(AliasCmdOp)