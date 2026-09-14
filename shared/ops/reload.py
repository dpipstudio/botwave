import inspect
from pathlib import Path
from typing import Any

import shared.prompt as prompt
from shared.dirutils import BW_PATH
from shared.logger import Log
from shared.ops import CliOp

class ReloadCliOp(CliOp):
    """
    The 'reload' command OP. This OP removes all entries from
    the registry and reloads them all. This allows a commands
    + custom commands + handlers refresh without restarting
    the process.
    """

    name = "reload"
    syntax = ""
    short_help = "Reload commands, custom commands and handlers"
    long_help = """\
Removes all registered operations, then reloads commands,
custom commands and handlers without restarting the process.
    """
    examples = [
        "reload"
    ]
    env_vars = {
        "HANDLERS_DIR": (f"{BW_PATH}/handlers", "The directory handlers and custom commands are loaded from")
    }

    async def handle(self, is_cmd: bool = False, cmd_parts: list[str] = []):
        Log.info("Reloading...")

        self.registry.operations.clear()
        self.registry.instances.clear()

        # obscure way to detect if we should load the server or local ops
        ops_dir = Path(inspect.getfile(self.owner.__class__)).parent / "ops"
        self.registry.from_dir(ops_dir)

        # since this file is located into shared/ops, we can load according to __file__
        self.registry.from_dir(Path(__file__).parent)

        self.owner.custom_commands.register(self.registry)
        self.owner.handlers_executor.register(self.registry)

        prompt.COMMANDS.clear()
        prompt.COMMANDS.update({op.name: op.syntax for op in self.registry.get_instances().values() if isinstance(op, CliOp)})

        Log.success("Reloaded")


def setup(reg: Any):
    reg.register(ReloadCliOp)