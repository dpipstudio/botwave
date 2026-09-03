from typing import Any

from shared.logger import Log
from shared.ops import CliOp

class StopOp(CliOp):
    """
    The 'stop' command OP. Stops the current broadcast
    if any. Also stops the ALSA listening.
    """

    name = "stop"
    syntax = ""
    short_help = "Stop the current broadcast"
    long_help = short_help
    examples = [
        "stop"
    ]
    env_vars = {}

    async def handle(self, silent: bool = False, is_cmd: bool = False, cmd_parts: list[str] = []):
        if is_cmd:
            self.owner.queue.manual_pause()

        if not self.owner.broadcasting and not silent:
            Log.warning("No broadcast is currently running")
            return
        
        self.owner.piwave_monitor.stop()

        if self.owner.piwave:
            try:
                self.owner.piwave.cleanup()

            except Exception as e:
                if not silent:
                    Log.error(f"Error stopping broadcast: {e}")

            finally:
                self.owner.piwave = None

        self.owner.alsa.stop()

        await self.registry.dispatch("handlers_onstop", context={"BW_BROADCAST_FILE": self.owner.current_file or ""})

        self.owner.broadcasting = False
        self.owner.tips.is_broadcasting = False
        self.owner.broadcast_start_time = None
        self.owner.current_file = None

        if not silent:
            Log.broadcast("Broadcast stopped")

        return True

def setup(reg: Any):
    reg.register(StopOp)