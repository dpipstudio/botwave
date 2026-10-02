import shlex
from typing import Any

from shared.logger import Log
from shared.ops import AliasOp, CliOp

class AliasCmdOp(CliOp):
    """
    The 'alias' command OP. Manages and list
    command aliases.
    """

    name = "alias"
    syntax = "<command> [value]"
    short_help = "Manage command aliases"
    long_help = """\
Creates, shows, lists and removes command aliases. An alias
is a shortcut name that runs a registered command, and any
extra arguments typed after it are appended to that command.

With a [value], creates the alias <command> so it runs
[value]. Without one, shows what the alias <command>
represents.

'alias list' shows every alias with the command it runs and
the syntax still missing after the arguments it already
provides. 'alias rm <name>' removes an alias.

Aliases are saved to a file and loaded at startup. They can
only run registered commands, can't reuse the name of an
existing command, and can't point to themselves. The names
'list' and 'rm' are reserved.
"""
    examples = [
        "alias list",
        "alias smf \"start myfile.wav\"",
        "alias rm smf"
    ]
    env_vars = {}

    async def handle(self, name: str = "", value: str = "", is_cmd: bool = False, cmd_parts: list[str] = []):
        if is_cmd:
            name, value = self.parse(cmd_parts)

            if not name:
                return

        match name:
            case "list":
                self.list_aliases()
                return

            case "rm":
                self.remove_alias(value)
                return

            case _:
                pass

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

        if command not in self.registry.operations:
            Log.error(f"'{value}' wants to execute '{command}' that is not a registered command.")
            Log.error("Please only register aliases for known commands")
            return

        existing = self.registry.instances.get(f"ALIAS_{name}")
        if name in self.registry.operations and not isinstance(existing, AliasOp):
            Log.error(f"'{name}' is already a command, pick another name")
            return

        if name == command:
            Log.error("An alias can't point to itself")
            return

        if "=" in name:
            Log.error("An alias can't have '=' in its name")
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

    def list_aliases(self):
        if not self.owner.aliases.aliases:
            Log.warning("No aliases are registered yet.")
            Log.warning(f"Create a new one with 'alias <alias_name> <value>'")
            return

        for alias in [a for a in self.registry.get_instances().values() if isinstance(a, AliasOp)]:
            Log.print(f"{alias.name}: {alias.original_name}", "yellow")
            Log.print(f"  Command: {alias.command}")
            Log.print(f"  Missing: {alias.syntax if alias.syntax else '/'}")
            Log.print("")

    def remove_alias(self, name: str):
        if name not in self.owner.aliases.aliases:
            Log.warning(f"No alias with the name '{name}' was found")
            return

        self.owner.aliases.remove(name)

        Log.success(f"Removed '{name}'")

def setup(reg: Any):
    reg.register(AliasCmdOp)