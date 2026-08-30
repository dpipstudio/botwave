import os
from pathlib import Path

from shared.env import Env

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
    
    def get_all(self) -> list[dict[str, str | list[str]]]:
        matches: list[dict[str, str | list[str]]] = []

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

                    # process help lines 
                    help_lines: list[str] = []
                    for line in lines[1:]:
                        line = line.rstrip("\n")

                        if line.startswith("#"):
                            # remove '#' and after char
                            help_lines.append(line[1:])
                        else:
                            break

                    matches.append({
                        "name": cmd_name,
                        "help": help_lines
                    })

            except:
                continue

        return matches