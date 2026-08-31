import os
from typing import Any

from shared.env import Env
from shared.logger import Log
from shared.ops import CliOp, GeneralOp
from shared.protocol import PROTOCOL_VERSION

class HandlersCliOp(CliOp):
    """
    The 'handlers' command OP. Lists current handlers if no
    argument provided, or displays the content of an handler file
    if the file exists. Overall just a HanderExecutor wrapper.
    """

    name = "handlers"
    syntax = "[filename]"

    async def handle(self, file: bool = False, is_cmd: bool = False, cmd_parts: list[str] = []):
        if is_cmd:
            file = self.parse(cmd_parts)

        if file:
            self.owner.handlers_executor.list_handler_commands(file)

        else:
            self.owner.handlers_executor.list_handlers()

    def parse(self, cmd_parts: list[str]) -> Any:
        return cmd_parts[0] if len(cmd_parts) > 0 else None

class HandlersEventsOp(GeneralOp):
    """
    The handler events system. Runs commands in specific handlers files
    depending on events dispatched by the server.

    Currently supports:
      - s_onready:      Triggers on server startup
      - s_onexit:       Triggers on server exit (exit command)
      - s_onstart:      Triggers on broadcast startup
      - s_onstop:       Triggers on broadcast stop
      - s_onconnect:    Triggers on client connect
      - s_ondisconnect: Triggers on client disconnect
      - s_onwsjoin:     Triggers on remote CLI connect
      - s_onwsleave:    Triggers on remote CLI disconnect
    """

    commands = {
        "handlers_onready": "onready",
        "handlers_onexit": "onexit",
        "handlers_onstart": "onstart",
        "handlers_onstop": "onstop",
        "handlers_onconnect": "onconnect",
        "handlers_ondisconnect": "ondisconnect",
        "handlers_onwsjoin": "onwsjoin",
        "handlers_onwsleave": "onwsleave"
    }

    async def onready(self, dir_path: str = "", context: dict[str, str] = {}, client_id: str = ""):
        if context:
            context.update(self.build_context(client_id))

        else:
            context = self.build_context(client_id)

        await self.owner.handlers_executor.run_handlers("s_onready", dir_path, context)

    async def onexit(self, dir_path: str = "", context: dict[str, str] = {}, client_id: str = ""):
        if context:
            context.update(self.build_context(client_id))

        else:
            context = self.build_context(client_id)

        await self.owner.handlers_executor.run_handlers("s_onexit", dir_path, context)


    async def onstart(self, dir_path: str = "", context: dict[str, str] = {}, client_id: str = ""):
        if context:
            context.update(self.build_context(client_id))

        else:
            context = self.build_context(client_id)

        await self.owner.handlers_executor.run_handlers("s_onstart", dir_path, context)


    async def onstop(self, dir_path: str = "", context: dict[str, str] = {}, client_id: str = ""):
        if context:
            context.update(self.build_context(client_id))

        else:
            context = self.build_context(client_id)

        await self.owner.handlers_executor.run_handlers("s_onstop", dir_path, context)

    async def onconnect(self, dir_path: str = "", context: dict[str, str] = {}, client_id: str = ""):
        if context:
            context.update(self.build_context(client_id))

        else:
            context = self.build_context(client_id)

        await self.owner.handlers_executor.run_handlers("s_onconnect", dir_path, context)

    async def ondisconnect(self, dir_path: str = "", context: dict[str, str] = {}, client_id: str = ""):
        if context:
            context.update(self.build_context(client_id))

        else:
            context = self.build_context(client_id)

        await self.owner.handlers_executor.run_handlers("s_ondisconnect", dir_path, context)

    async def onwsjoin(self, dir_path: str = "", context: dict[str, str] = {}, client_id: str = ""):
        if context:
            context.update(self.build_context(client_id))

        else:
            context = self.build_context(client_id)

        await self.owner.handlers_executor.run_handlers("s_onwsjoin", dir_path, context)
        self.owner.rc_clients += 1


    async def onwsleave(self, dir_path: str = "", context: dict[str, str] = {}, client_id: str = ""):
        if context:
            context.update(self.build_context(client_id))

        else:
            context = self.build_context(client_id)

        await self.owner.handlers_executor.run_handlers("s_onwsleave", dir_path, context)
        self.owner.rc_clients -= 1

    def build_context(self, client_id: str = "") -> dict[str, str]:
        ctx = {}

        try:
            argv_env = {f"BW_ARGV{i}": str(v) for i, v in enumerate(self.owner.last_argv)}

            ws_port = Env.get("PORT")

            ctx = {
                **argv_env,
                "BW_SYSTEM_HOSTNAME": os.uname().nodename,
                "BW_SYSTEM_MACHINE": os.uname().machine,
                "BW_SYSTEM_SYSTEM": os.uname().sysname,
                "BW_SYSTEM_PROTO": PROTOCOL_VERSION,
                "BW_UPLOAD_DIR": Env.get("UPLOAD_DIR") or "",
                "BW_HANDLERS_DIR": Env.get("HANDLERS_DIR") or "",
                "BW_WS_PORT": ws_port if ws_port else "0",
                "BW_PASSKEY_SET": "true" if Env.get("PASSKEY") else "false",
                "BW_TRANSACTION_ID": Log.transaction_id.get() or "",
                "BW_SERVER_CONNECTED_CLIENTS": ",".join(
                        client.machine_info.get("hostname", "unknown") 
                        for client in self.owner.clients.values()
                    ),
            }
        except:
            ...

        # Client info (only when a specific client is referenced)
        if client_id and client_id in self.owner.clients:
            client = self.owner.clients[client_id]
            info = client.machine_info
            ctx.update({
                "BW_CLIENT_ID": client_id,
                "BW_CLIENT_HOSTNAME": info.get("hostname", "unknown"),
                "BW_CLIENT_MACHINE": info.get("machine", "unknown"),
                "BW_CLIENT_SYSTEM": info.get("system", "unknown"),
                "BW_CLIENT_PROTO": client.protocol_version,
                "BW_CLIENT_CONNECTED_AT": client.connected_at.strftime("%Y-%m-%d %H:%M:%S"),
            })

        return ctx

        
def setup(reg: Any):
    reg.register(HandlersCliOp)
    reg.register(HandlersEventsOp)