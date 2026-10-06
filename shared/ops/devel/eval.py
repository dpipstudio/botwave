import inspect
from pprint import pformat
from typing import Any

from shared.env import Env
from shared.logger import Log
from shared.ops import CliOp

class EvalOp(CliOp):
    """
    The 'eval' development command OP. Evaluates a python expression and
    prints what it returns. Awaitables are awaited first, so
    async methods can be tested directly.

    'self' is this op, so the running component is 'self.owner'
    and the registry is 'self.registry'. 'Log' and 'Env' are
    available too.
    """

    name = "eval"
    syntax = "<expression>"
    short_help = "Evaluate a python expression (devel)"
    long_help = """\
Evaluates a python <expression> and prints the result, if any.

'self' is this op ('self.owner' being the running component),
'Log' and 'Env' are available. Awaitables are awaited.

Only for development, it can run anything.
"""
    examples = [
        "eval self.owner.aliases.aliases",
        "eval \"Log.print('hello')\"",
        "eval self.registry.dispatch('status')"
    ]
    env_vars = {}

    async def handle(self, expression: str = "", is_cmd: bool = False, cmd_parts: list[str] = []):
        if is_cmd:
            expression = self.parse(cmd_parts)

            if not expression:
                return

        try:
            result = eval(expression, {"self": self, "Log": Log, "Env": Env})

            if inspect.isawaitable(result):
                result = await result

        except Exception as e:
            Log.error(f"{type(e).__name__}: {e}")
            return

        if result is not None:
            Log.print(pformat(result))

    def parse(self, cmd_parts: list[str]) -> Any:
        if len(cmd_parts) < 1:
            Log.error("Usage: eval <expression>")
            return None

        return cmd_parts[0]

def setup(reg: Any):
    reg.register(EvalOp)