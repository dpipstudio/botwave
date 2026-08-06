from pathlib import Path
import time

from shared.env import Env
from shared.logger import Log
from shared.ops import CliOp

class StatusOp(CliOp):
    """
    The 'status' command OP. Shows the state of the
    local client.
    """

    name = "status"

    async def handle(self, is_cmd: bool = False, cmd_parts: str = None):
        if self.owner.broadcasting and self.owner.current_file:
            Log.print("On Air", "bright_green")
            Log.print(f"File       : {Path(self.owner.current_file).name}", "white")
            if self.owner.piwave:
                Log.print(f"Frequency  : {self.owner.piwave.get_status()['frequency']} MHz", "white")

            if self.owner.broadcast_start_time:
                elapsed = int(time.time() - self.owner.broadcast_start_time)
                h, m, s = elapsed // 3600, (elapsed % 3600) // 60, elapsed % 60
                Log.print(f"Uptime     : {h:02d}:{m:02d}:{s:02d}", "white")
        else:
            Log.print("Idle", "orange")

        if Env.get("REMOTE_CMD_PORT"):
            Log.print(f"RC Port    : {Env.get('REMOTE_CMD_PORT')}", "white")
            Log.print(f"RC Clients : {self.owner.rc_clients}", "white")
            Log.print(f"Passkey    : {'yes' if Env.get('PASSKEY') else 'no'}", "white")


def setup(reg):
    reg.register(StatusOp)