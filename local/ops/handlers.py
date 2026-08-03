import os

from shared.env import Env
from shared.logger import Log
from shared.ops import CliOp, GeneralOp
from shared.protocol import PROTOCOL_VERSION

class HandlersCliOp(CliOp):
    name = "handlers"
    syntax = "[filename]"

    async def handle(self, file: bool = None, is_cmd: bool = False, cmd_parts: list = []):
        if is_cmd:
            file = self.parse(cmd_parts)

        if file:
            self.owner.handlers_executor.list_handler_commands(file)

        else:
            self.owner.handlers_executor.list_handlers()

    def parse(self, cmd_parts):
        return cmd_parts[0] if len(cmd_parts) > 0 else None

class HandlersEventsOp(GeneralOp):
    commands = {
        "handlers_onready": "onready",
        "handlers_onexit": "onexit",
        "handlers_onstart": "onstart",
        "handlers_onstop": "onstop",
        "handlers_onwsjoin": "onwsjoin",
        "handlers_onwsleave": "onwsleave"
    }

    async def onready(self, dir_path: str = None, context: dict = None):
        if context:
            context.update(self.build_context())

        else:
            context = self.build_context()

        print(context)

        await self.owner.handlers_executor.run_handlers("l_onready", dir_path, context)

    async def onexit(self, dir_path: str = None, context: dict = None):
        if context:
            context.update(self.build_context())

        else:
            context = self.build_context()

        await self.owner.handlers_executor.run_handlers("l_onexit", dir_path, context)


    async def onstart(self, dir_path: str = None, context: dict = None):
        if context:
            context.update(self.build_context())

        else:
            context = self.build_context()

        await self.owner.handlers_executor.run_handlers("l_onstart", dir_path, context)


    async def onstop(self, dir_path: str = None, context: dict = None):
        if context:
            context.update(self.build_context())

        else:
            context = self.build_context()

        await self.owner.handlers_executor.run_handlers("l_onstop", dir_path, context)


    async def onwsjoin(self, dir_path: str = None, context: dict = None):
        if context:
            context.update(self.build_context())

        else:
            context = self.build_context()

        await self.owner.handlers_executor.run_handlers("l_onwsjoin", dir_path, context)


    async def onwsleave(self, dir_path: str = None, context: dict = None):
        if context:
            context.update(self.build_context())

        else:
            context = self.build_context()

        await self.owner.handlers_executor.run_handlers("l_onwsleave", dir_path, context)

    def build_context(self) -> dict:
        ctx = {}

        try:
            argv_env = {f"BW_ARGV{i}": str(v) for i, v in enumerate(self.owner.last_argv)}

            ctx = {
                **argv_env,
                "BW_SYSTEM_HOSTNAME": os.uname().nodename,
                "BW_SYSTEM_MACHINE": os.uname().machine,
                "BW_SYSTEM_SYSTEM": os.uname().sysname,
                "BW_SYSTEM_PROTO": PROTOCOL_VERSION,
                "BW_UPLOAD_DIR": Env.get("UPLOAD_DIR", ""),
                "BW_HANDLERS_DIR": Env.get("HANDLERS_DIR", ""),
                "BW_WS_PORT": str(Env.get_int("REMOTE_CMD_PORT")) if Env.get_int("REMOTE_CMD_PORT") else "0",
                "BW_PASSKEY_SET": "true" if Env.get("PASSKEY") else "false",
                "BW_TRANSACTION_ID": Log.transaction_id.get() or "",
            }

        except:
            ...

        return ctx

        
def setup(reg):
    reg.register(HandlersCliOp)
    reg.register(HandlersEventsOp)