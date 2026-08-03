from shared.logger import Log
from shared.ops import CliOp
from shared.registry import UpperException

class ExitOp(CliOp):
    name = "exit"

    async def handle(self, is_cmd: bool = False, cmd_parts: list = []):
        self.owner.running = False
        if self.owner.broadcasting:
            await self.registry.dispatch("stop")

        #TODO: check if those signals are really useful
        """
        if self.original_sigint_handler:
            signal.signal(signal.SIGINT, self.original_sigint_handler)

        if self.original_sigterm_handler:
            signal.signal(signal.SIGTERM, self.original_sigterm_handler)
        """

        self.owner.tips.stop()

        await self.registry.dispatch("handlers_onexit")

        Log.client("Local client stopped")
        raise UpperException("exit")

def setup(reg):
    reg.register(ExitOp)