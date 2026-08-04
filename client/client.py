import asyncio
import os
from pathlib import Path
import sys

# using this to access to the shared dir files
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from shared.env import Env
from shared.logger import Log
from shared.protocol import Commands, ProtocolParser
from shared.registry import Registry, UpperException
from shared.tips import TipEngine

class BotWaveClient:
    def __init__(self):
        self.ws_client = None
        self.http_client = None
        self.proto = None

        self.running = False
        self.registered = False
        self.client_id = None

        self.registry = Registry(self)
        self.tips = TipEngine(is_server=False)

    async def handle_message(self, message: str):
        Log.print(message)

        parsed = ProtocolParser.parse_command(message)
        cmd = parsed['command']

        if cmd not in vars(Commands).values():
            found = False

        else:
            found = await self.registry.dispatch(cmd, parsed=parsed)
        
        if not found:
            Log.warning(f"Unknown command: {cmd}")
            await self.proto.reply(parsed, Commands.ERROR, message=f"Unknown command: {cmd}. Perhaps a protocol mismatch?")


async def main():
    client = BotWaveClient()
    client.registry.from_dir(Path(__file__).resolve().parent / "ops")

    Env.set("SERVER_HOST", "localhost")
    Env.set("SERVER_PORT", "9938")
    
    try:
        await client.registry.dispatch("client_connect")

    except UpperException:
        #TODO: await client.registry.dispatch("client_stop")
        sys.exit(1)

    client.running = True
    client.tips.start()

    try:
        await client.ws_client.wait_for_disconnect()

    except (KeyboardInterrupt, asyncio.CancelledError):
        Log.warning("Shutting down...")

    finally:
        #TODO: await client.registry.dispatch("client_stop")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())