from pprint import pformat
from typing import Any

from shared.logger import Log
from shared.ops import CliOp

class PrintOp(CliOp):
    """
    The 'print' development command OP. Prints the value of
    one or more dotted paths (self.owner.piwave), starting
    from this op or 'Log'.
    """

    name = "print"
    syntax = "<paths>"
    short_help = "Print the value of an attribute path (devel)"
    long_help = """\
Prints the value of one or more <paths>. A path starts with
'self' (this op, so 'self.owner' is the running component),
'Log' or followed by attribute names separated by dots.

Only for development.
"""
    examples = [
        "print self.owner.piwave",
        "print self.owner.aliases.aliases",
        "print self.owner.broadcasting self.owner.current_file"
    ]
    env_vars = {}

    async def handle(self, paths: list[str] = [], is_cmd: bool = False, cmd_parts: list[str] = []):
        if is_cmd:
            paths = self.parse(cmd_parts)

            if not paths:
                return

        roots = {"self": self, "Log": Log}

        for path in paths:
            root, *attrs = path.split(".")

            if root not in roots:
                Log.error(f"'{root}' is not a valid start, use one of: {', '.join(roots)}")
                continue

            value = roots[root]

            try:
                for attr in attrs:
                    value = getattr(value, attr)

            except AttributeError as e:
                Log.error(f"{path}: {e}")
                continue

            Log.print(f"({path})", style="bright_blue", end=" ")
            Log.print(pformat(value), style="white")

    def parse(self, cmd_parts: list[str]) -> Any:
        if len(cmd_parts) < 1:
            Log.error("Usage: print <paths>")
            return None

        return cmd_parts

def setup(reg: Any):
    reg.register(PrintOp)