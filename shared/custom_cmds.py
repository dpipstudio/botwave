import os
import shlex
from pathlib import Path
from typing import Any

from shared.env import Env
from shared.logger import Log
from shared.ops import CliOp
from shared.registry import Registry

class CustomCommand:
    path: Path
    name: str = ""
    syntax: str = ""
    short_help: str = ""
    long_help: str = ""

class CCMD:
    def __init__(self, is_server: bool = True):
        self.is_server = is_server

    @property
    def handlers_dir(self):
        return Env.get("HANDLERS_DIR", "/opt/BotWave/handlers/")

    def register(self, registry: Registry):
        if not Path(self.handlers_dir).is_dir():
            Log.warning(f"{self.handlers_dir} does not exist, skipping custom commands registration")
            return
        
        ccmds = self.get_all()

        for ccmd in ccmds:
            try:
                with open(ccmd.path, "r", encoding="utf-8") as f:
                    content = f.readlines()

                async def handle(self: Any, ccmd: CustomCommand = ccmd, content: list[str] = content, cmd_parts: list[str] = [], is_cmd: bool = False):
                    await self.owner.handlers_executor.execute_handler(
                        str(ccmd.path),
                        self.registry.get_instances()["HandlersEventsOp"].build_context(),
                        silent=True,
                        lines=content
                    )

                op = type(f"CCMD_{ccmd.name}", (CliOp,), {
                    "handle": handle
                })
                op.name = ccmd.name
                op.syntax = ccmd.syntax
                op.short_help = ccmd.short_help
                op.long_help = ccmd.long_help
                op.examples = []
                op.env_vars = {}

                registry.register(op)

            except Exception as e:
                Log.warning(f"Failed to load '{ccmd.path}': {e}")
    
    def get_all(self) -> list[CustomCommand]:
        matches: list[CustomCommand] = []

        handlers_path = Path(self.handlers_dir)
        for file in handlers_path.rglob("*.cmd"):

            full_path = handlers_path / file
            if not os.path.isfile(full_path):
                continue

            cmd_name = file.stem
            shebang = f"#!/{'server' if self.is_server else 'local'}/{cmd_name}"
            wildcard = f"#!/*/{cmd_name}"

            try:
                with open(full_path, "r") as f:
                    lines = f.readlines()
                    if not lines:
                        continue

                    first_line = lines[0].rstrip("\n")
                    if first_line != shebang and first_line != wildcard:
                        continue

                    ccmd = CustomCommand()
                    ccmd.path = full_path
                    ccmd.name = cmd_name

                    # consider commands with #> and #? as v2
                    if any((line.startswith("#>") or line.startswith("#?")) for line in lines):
                        Log.debug(f"ccmd parsing: treating {file} as v2")
                        self.parse_ccmd_v2(ccmd, lines)

                    else:
                        self.parse_ccmd_v0(ccmd, lines)

                    matches.append(ccmd)

            except Exception as e:
                Log.error(f"Error while parsing subcommand {file}: {e}")
                continue

        return matches

    def parse_ccmd_v0(self, ccmd: CustomCommand, lines: list[str]):
        help_lines: list[str] = []
        for line in lines[1:]:
            line = line.rstrip("\n")

            if line.startswith("#"):
                # remove '#' and after char
                help_lines.append(line[1:])
            else:
                break

        
        ccmd.syntax = help_lines[0].lower().replace(ccmd.name, "") if len(help_lines) > 0 else "Unknown syntax"
        ccmd.short_help = f"The {ccmd.name} custom command"
        ccmd.long_help = ' '.join(help_lines[1:])


    def parse_ccmd_v2(self, ccmd: CustomCommand, lines: list[str]):
        # parse meta
        for line in lines:
            if line.startswith("#>"):
                self.parse_meta_v2(ccmd, line)

            elif line.startswith("#?"):
                line = line[3:].rstrip()
                ccmd.long_help += line + "\n"

        if not (ccmd.name and ccmd.short_help and ccmd.long_help):
            raise ValueError("ccmd is being parsed as ccmdv2, but it doesn't provide all the required meta fields")

    def parse_meta_v2(self, ccmd: CustomCommand, line: str):
        line = line[2:].strip()
        parts = shlex.split(line)

        if len(parts) != 2:
            raise ValueError(f"ccmdmeta parsing error: expected '#> keyword \"value\"', got: {line}")

        command = parts[0]
        value = parts[1]

        if command == "syntax":
            ccmd.syntax = value

        elif command == "short_help":
            ccmd.short_help = value

        else:
            raise ValueError(f"unexpected keyword while parsing ccmdmeta: {command}")