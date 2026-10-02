import shlex
from pathlib import Path

from shared.dirutils import BW_PATH
from shared.logger import Log
from shared.ops import AliasOp, CliOp
from shared.prompt import COMMANDS
from shared.registry import Registry

class Aliases:
    def __init__(self, is_server: bool = True) -> None:
        self.registry: Registry | None = None
        self.aliasfile = Path(BW_PATH) / f"{'s' if is_server else 'l'}_aliases"

        # the file might not exist yet
        self.aliasfile.touch()

        # for quick lookup
        self.aliases: dict[str, str] = {}

    def register(self, registry: Registry):
        self.registry = registry

        for alias in self.load():
            registry.register(alias)

    def load(self) -> list[type[AliasOp]]:
        aliases: list[type[AliasOp]] = []

        try:
            with open(self.aliasfile) as f:
                for line in f:
                    name, value = self.__parse(line)

                    if not name or not value:
                        continue

                    op = self.__build_op(name, value)

                    aliases.append(op)
                    self.aliases[name] = value

                Log.debug(f"Loaded {len(aliases)} aliases")

        except Exception as e:
            Log.warning(f"Failed to load aliases: {e}")

        return aliases

    def get(self, name: str) -> str | None:
        """return the command executed by the given alias"""
        return self.aliases.get(name)

    def set(self, name: str, value: str):
        if not self.registry:
            raise RuntimeError("Called Aliases.set when Aliases.registry is None. Cannot register.")
        
        try:
            with open(self.aliasfile, "a") as f:
                f.write(f"{name}={value}\n")

        except Exception as e:
            Log.warning(f"Failed to write alias to file: {e}")

        self.aliases[name] = value

        op = self.__build_op(name, value)
        self.registry.register(op)

        COMMANDS.update({ op.name: op.syntax })

    def remove(self, name: str):
        """
        Removes the given alias from the aliasfile and the registry
        """
        if name not in self.aliases:
            return

        if not self.registry:
            raise RuntimeError("Called Aliases.remove when Aliases.registry is None. Cannot unregister.")

        try:
            with open(self.aliasfile) as f:
                lines = f.readlines()

            kept = [line for line in lines if self.__parse(line)[0] != name]

            with open(self.aliasfile, "w") as f:
                f.writelines(kept)

        except Exception as e:
            Log.warning(f"Failed to remove alias from file: {e}")
            return

        del self.aliases[name]

        self.registry.operations.pop(name, None)
        self.registry.instances.pop(f"ALIAS_{name}", None)

        COMMANDS.pop(name, None)

    def __parse(self, line: str) -> tuple[str | None, str | None]:
        """
        Parses a aliasfile line. Expects the line to be formatted
        like the following:
        my-alias=alias content

        Returns (name, value) if the given line is a valid alias
        line. Otherwise returns (None, None)
        """

        name, sep, value = line.partition('=')

        if not sep or not name.strip():
            return (None, None)

        return (name.strip(), value.strip())

    def __build_op(self, name: str, value: str) -> type[AliasOp]:
        """
        Builds an AliasOp from the given name and value
        """

        op = type(f"ALIAS_{name}", (AliasOp,), {})
        op.name = name
        op.command = value

        parts = shlex.split(value)
        command = parts[0] if len(parts) > 0 else ""
        op.original_name = command

        if not self.registry:
            return op

        cmd_op = next(
            (op for op in self.registry.get_instances().values()
            if isinstance(op, CliOp) and op.name == command),
            None
        )

        cmd_op = cmd_op if isinstance(cmd_op, CliOp) else None

        if not cmd_op:
            return op

        cmd_op_syntax = cmd_op.syntax.split(' ')
        missing_syntax = ' '.join(cmd_op_syntax[len(shlex.split(value)) - 1:])

        op.syntax = missing_syntax

        return op