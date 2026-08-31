import time
from pathlib import Path
from typing import Any

from shared.ops import GeneralOp
from shared.protocol import Commands
from shared.protomanager import ParsedCommand

class StatusOp(GeneralOp):
    """
    The OP handling Commands.STATUS. Returns the
    current client status with information such as 
    the broadcast status, uptime, frequency, and file
    """

    commands = {Commands.STATUS: "status"}

    async def status(self, parsed: ParsedCommand):
        if self.owner.broadcasting and self.owner.current_file:
            status = "onair"
            file = Path(self.owner.current_file).name
            freq = self.owner.piwave.get_status()["frequency"]
            uptime = "??:??:??"
            
            if self.owner.broadcast_start_time:
                elapsed = int(time.time() - self.owner.broadcast_start_time)
                h, m, s = elapsed // 3600, (elapsed % 3600) // 60, elapsed % 60
                uptime = f"{h:02d}:{m:02d}:{s:02d}"
        
            await self.owner.proto.reply(
                parsed,
                Commands.OK,
                status=status,
                file=file,
                frequency=freq,
                uptime=uptime
            )

        else:
            await self.owner.proto.reply(parsed, Commands.OK, status = "idle")

def setup(reg: Any):
    reg.register(StatusOp)