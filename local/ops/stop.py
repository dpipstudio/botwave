from shared.logger import Log
from shared.ops import CliOp

class StopOp(CliOp):
    name = "stop"

    async def handle(self, is_cmd: bool = False, cmd_parts: str = None):
        if is_cmd:
            self.owner.queue.manual_pause()

        if not self.owner.broadcasting:
            Log.warning("No broadcast is currently running")
            return
        
        self.owner.piwave_monitor.stop()

        if self.owner.piwave:
            try:
                self.owner.piwave.cleanup()

            except Exception as e:
                Log.error(f"Error stopping broadcast: {e}")

            finally:
                self.piwave = None

        self.owner.alsa.stop()

        self.owner.broadcasting = False
        self.owner.broadcast_start_time = None
        self.owner.current_file = None

        #TODO: self.onstop_handlers(context={**self._build_context(), "BW_BROADCAST_FILE": self.current_file or ""})
        await self.owner.registry.dispatch("handlers_stop", context={"BW_BROADCAST_FILE": self.owner.current_file or ""})
        Log.broadcast("Broadcast stopped")

        return True
