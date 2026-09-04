import re
from typing import Any, Callable

from shared.logger import Log
from shared.ops import CliOp

class CommandInfo:
    name: str
    is_custom: bool
    required_syntax: str
    full_syntax: str
    short_help: str
    long_help: str
    full_help: Callable[..., None]

class HelpOp(CliOp):
    """
    The 'help' command OP.
    Lists every command and its syntax.
    If the command has 'target' in its syntax, show
    targets help. Also handles custom commands.
    """

    name = "help"
    syntax = "[commands]"
    short_help = "Show general or command-specific help"
    long_help = """\
Without arguments, lists every available command with a
short description.

If one or more [commands] are given, shows the full help
for each one: its syntax, a detailed description, examples
and any related environment variables.

Custom commands (.cmd files) are included in both views.
"""
    examples = [
        "help",
        "help start",
        "help start live my_customcmd"
    ]
    env_vars = {}

    async def handle(self, commands: list[str] = [], is_cmd: bool = False, cmd_parts: list[str] = []):
        if is_cmd:
            commands = self.parse(cmd_parts)

        all_commands = [
            self.get_cmd_info(cmd)
            for cmd in self.registry.get_instances().values()
            if isinstance(cmd, CliOp)
        ]

        all_commands += [
            self.get_ccmd_info(ccmd)
            for ccmd in self.owner.custom_commands.get_all()
        ]

        if commands:
            for index, command in enumerate(commands, start=1):
                if command in [cmd.name for cmd in all_commands]:
                    cmd_info = next((cmd for cmd in all_commands if cmd.name == command))

                    Log.print("›", "bright_green", end=" ")
                    Log.print(
                        f"{cmd_info.name if not cmd_info.is_custom else ''} {cmd_info.full_syntax or cmd_info.name}".strip(),
                        "yellow",
                        end="\n\n"
                        )

                    cmd_info.full_help()
                
                else:
                    Log.warning(f"Command '{command}' not found")

                if index != len(commands):
                    Log.print("\n---------------------------------", "green", end="\n\n")

            return

        self.show_help(all_commands)

    def parse(self, cmd_parts: list[str]):
        return cmd_parts

    def get_cmd_info(self, cmd_op: CliOp) -> CommandInfo:
        cmd_info = CommandInfo()
        cmd_info.name = cmd_op.name
        cmd_info.is_custom = False
        cmd_info.full_syntax = cmd_op.syntax
        cmd_info.short_help = cmd_op.short_help
        cmd_info.long_help = cmd_op.long_help

        # only keep stuff inside '<>'
        syntax = cmd_op.syntax
        cmd_info.required_syntax = ' '.join(re.findall(r'<[^>]*>', syntax))

        def full_help():
            Log.print(cmd_op.long_help, end="")

            if len(cmd_op.examples) != 0:
                Log.print("")
                Log.print("Examples:" if len(cmd_op.examples) > 1 else "Example:")

                for example in cmd_op.examples:
                    Log.print(f"  - {Log.COLORS.get('cyan')}{example}", "reset")

            if len(cmd_op.env_vars) != 0:
                Log.print("")
                Log.print(f"Environment variables:")

                for name, (default, usage) in cmd_op.env_vars.items():
                    Log.print(f"  - {name} ({default}): {usage}")

            if "target" in cmd_info.full_syntax:
                self.print_targets()

        cmd_info.full_help = full_help

        return cmd_info

    def get_ccmd_info(self, custom_command: dict[Any, Any]) -> CommandInfo:
        cmd_info = CommandInfo()
        cmd_info.name = custom_command["name"]
        cmd_info.is_custom = True

        help = custom_command["help"]
        cmd_info.required_syntax = ' '.join(re.findall(r'<[^>]*>', help[0])) if len(help) > 0 else ""
        cmd_info.full_syntax = help[0].strip() if len(help) > 0 else ""
        cmd_info.short_help = help[1].strip() if len(help) > 1 else f"The {cmd_info.name} custom command"
        cmd_info.long_help = '\n'.join(help)

        def full_help():
            Log.print(cmd_info.long_help)

        cmd_info.full_help = full_help

        return cmd_info

    def show_help(self, commands: list[CommandInfo]):
        is_server = any("target" in cmd.full_syntax for cmd in commands)

        Log.header(f"BotWave {'Server' if is_server else 'Local Client'} - Help")
        Log.section("Available Commands")

        self.list_commands(commands)

        if is_server:
            self.print_targets()

        Log.print("\nUse 'help [command]' to see specific help about a command")

    def print_targets(self):
        Log.print("")
        
        Log.print("Targets:")
        Log.print("  'all'                 All connected clients")
        Log.print("  client_id             Specific client by ID")
        Log.print("  hostname              Client by hostname")
        Log.print("  Comma-separated list  Multiple clients")
        Log.print("  Examples:")
        Log.print(f"    - {Log.COLORS.get('cyan')}pi1,pi2", "reset")
        Log.print(f"    - {Log.COLORS.get('cyan')}all", "reset")
        Log.print(f"    - {Log.COLORS.get('cyan')}kitchen-pi", "reset")

    def list_commands(self, commands: list[CommandInfo]):

        longest_cmd = max(len(f"{cmd.name} {cmd.required_syntax}") for cmd in commands)
        padding = longest_cmd + 4

        for cmd in commands:
            Log.print(f"{cmd.name} {cmd.required_syntax}".ljust(padding) + cmd.short_help)


def setup(reg: Any):
    reg.register(HelpOp)