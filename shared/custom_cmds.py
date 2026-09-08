import os
import re
import shlex
from pathlib import Path

from shared.env import Env
from shared.logger import Log

class CustomCommand:
    path: Path
    version: int = 0
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
    
    def exists(self, command: str) -> bool:
        """
        Checks if a custom command file exists and has the correct shebang
        """
        
        path = os.path.join(self.handlers_dir, f"{command}.cmd")

        if not os.path.isfile(path):
            return False
        
        shebang = f"#!/{'server' if self.is_server else 'local'}/{command}"
        wildcard = f"#!/*/{command}"

        with open(path, 'r') as f:
            first_line = f.readline().strip()

        return first_line == shebang or first_line == wildcard
    
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
                line = line[2:].strip()
                ccmd.long_help += line + "\n"

        if not (ccmd.name and ccmd.version and ccmd.syntax and ccmd.short_help and ccmd.long_help):
            raise ValueError("ccmd is declared as v2, but it doesn't provide all the required meta fields")

    def parse_meta_v2(self, ccmd: CustomCommand, line: str):
        line = line[2:].strip()
        parts = shlex.split(line)

        if len(parts) != 2:
            raise ValueError(f"ccmdmeta parsing error: expected '#> command \"value\"', got: {line}")

        command = parts[0]
        value = parts[1]

        if command == "cmdver":
            if not bool(re.fullmatch(r'v\d+', value)):
                raise ValueError(f"cmdver requires a valid version as value (vN), got {value}")

            ccmd.version = int(value[1:])

        elif command == "syntax":
            ccmd.syntax = value

        elif command == "short_help":
            ccmd.short_help = value

        else:
            raise ValueError(f"unexpected command while parsing ccmdmeta: {command}")