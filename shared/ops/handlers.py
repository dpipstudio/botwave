from typing import Any

from shared.dirutils import BW_PATH
from shared.ops import CliOp

class HandlersCliOp(CliOp):
    """
    The 'handlers' command OP. Lists current handlers if no
    argument provided, or displays the content of an handler file
    if the file exists. Overall just a HandlerExecutor wrapper.
    """

    name = "handlers"
    syntax = "[filename]"
    short_help = "List all handlers and custom commands available"
    long_help = """\
Lists all handlers (.hdl and .shdl) and custom commands
(.cmd) files in the handlers directory.
If a [filename] is provided, displays the content of that file.
"""
    examples = [
        "handlers",
        "handlers hello.cmd"
    ]
    env_vars = {
        "HANDLERS_DIR": (f"{BW_PATH}/handlers", "The directory handlers are located into")
    }

    async def handle(self, file: str = "", is_cmd: bool = False, cmd_parts: list[str] = []):
        if is_cmd:
            file = self.parse(cmd_parts)

        if file:
            self.owner.handlers_executor.list_handler_commands(file)

        else:
            self.owner.handlers_executor.list_handlers()

    def parse(self, cmd_parts: list[str]) -> Any:
        return cmd_parts[0] if len(cmd_parts) > 0 else None


def setup(reg: Any):
    reg.register(HandlersCliOp)