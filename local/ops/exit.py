from shared.logger import Log
from shared.ops import CliOp
from shared.registry import UpperException

class ExitOp(CliOp):
    """
    The 'exit' command OP. Completely stops the local client by
    raising an UpperException that gets caught in main() after cleaning up
    """

    name = "exit"

    async def handle(self, is_cmd: bool = False, cmd_parts: list = []):
        self.owner.running = False
        if self.owner.broadcasting:
            await self.registry.dispatch("stop")

        self.owner.tips.stop()

        await self.registry.dispatch("handlers_onexit")

        Log.client("Local client stopped")
        raise UpperException("exit")

def setup(reg):
    reg.register(ExitOp)