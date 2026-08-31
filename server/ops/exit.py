from typing import Any

from shared.logger import Log
from shared.ops import CliOp
from shared.registry import UpperException

class ExitOp(CliOp):
    """
    The 'exit' command OP. Completely stops the server by
    raising an UpperException that gets caught in main() after cleaning up
    """

    name = "exit"

    async def handle(self, is_cmd: bool = False, cmd_parts: list[str] = []):
        if not self.owner.running:
            return

        Log.server("Shutting down server...")

        if self.owner.clients:
            await self.registry.dispatch(
                "kick",
                targets=self.owner.parse_targets("all"),
                reason="Server is shutting down"
            )
        
        if self.owner.ws_server:
            await self.owner.ws_server.stop()
            Log.server("Main socket stopped")
        
        if self.owner.http_server:
            await self.owner.http_server.stop()
            Log.server("File transfer (HTTP) server stopped")

        self.owner.tips.stop()

        await self.registry.dispatch("handlers_onexit")
        
        self.owner.running = False
        Log.success("Server shutdown complete")

        raise UpperException("exit")

def setup(reg: Any):
    reg.register(ExitOp)