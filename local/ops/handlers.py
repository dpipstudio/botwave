import os
from typing import Any

from shared.env import Env
from shared.logger import Log
from shared.ops import GeneralOp
from shared.protocol import PROTOCOL_VERSION

class HandlersEventsOp(GeneralOp):
    """
    The handler events system. Runs commands in specific handlers files
    depending on events dispatched by the local client.

    Currently supports:
      - s_onready:   Triggers on local client startup
      - s_onexit:    Triggers on local client exit (exit command)
      - s_onstart:   Triggers on broadcast startup
      - s_onstop:    Triggers on broadcast stop
      - s_onwsjoin:  Triggers on remote CLI connect
      - s_onwsleave: Triggers on remote CLI disconnect
    """

    commands = {
        "handlers_onready": "onready",
        "handlers_onexit": "onexit",
        "handlers_onstart": "onstart",
        "handlers_onstop": "onstop",
        "handlers_onwsjoin": "onwsjoin",
        "handlers_onwsleave": "onwsleave"
    }

    async def onready(self,context: dict[str, str] = {}):
        await self.run_by_prefix("l_onready", context)

    async def onexit(self, context: dict[str, str] = {}):
        await self.run_by_prefix("l_onexit", context)

    async def onstart(self, context: dict[str, str] = {}):
        await self.run_by_prefix("l_onstart", context)

    async def onstop(self, context: dict[str, str] = {}):
        await self.run_by_prefix("l_onstop", context)

    async def onwsjoin(self, context: dict[str, str] = {}):
        await self.run_by_prefix("l_onwsjoin", context)
        self.owner.rc_clients += 1

    async def onwsleave(self, context: dict[str, str] = {}):
        await self.run_by_prefix("l_onwsleave", context)
        self.owner.rc_clients -= 1

    async def run_by_prefix(self, prefix: str, context: dict[str, str]):
        context.update(self.build_context())

        matches = [
            i.removeprefix("HDL_")
            for i in self.registry.get_instances().keys()
            if i.startswith(f"HDL_{prefix}")
        ]

        for match in sorted(matches):
            await self.registry.dispatch(match, context=context)

    def build_context(self) -> dict[str, str]:
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

        
def setup(reg: Any):
    reg.register(HandlersEventsOp)