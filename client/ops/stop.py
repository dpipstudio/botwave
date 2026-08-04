import asyncio
from datetime import datetime, timezone
from pathlib import Path
from piwave import PiWave
from piwave.backends import backend_classes
import time

from shared.bw_custom import BWCustom
from shared.env import Env
from shared.logger import Log
from shared.ops import GeneralOp
from shared.protocol import Commands
from shared.security import PathValidator, SecurityError

class StopOp(GeneralOp):
    commands = {
        Commands.STOP: "stop",
        "stop_broadcast": "stop_broadcast"
    }

    async def stop(self, parsed):
        try:
            if not self.owner.broadcasting:
                await self.owner.proto.reply(
                    parsed,
                    Commands.ERROR,
                    message="No broadcast running"
                )
                return

            await self.stop_broadcast()

            await self.owner.proto.reply(
                parsed,
                Commands.OK,
                message="Broadcast stopped"
            )

        except Exception as e:
            Log.error(f"Stop error: {e}")
            await self.owner.proto.reply(
                parsed,
                Commands.ERROR,
                message=str(e)
            )

    async def stop_broadcast(self, silent: bool = False):
        self.owner.piwave_monitor.stop()

        if self.owner.stream_active:
            self.owner.stream_active = False
            await asyncio.sleep(0.2)

        if self.owner.feed_task and not self.owner.feed_task.done():
            self.owner.feed_task.cancel()

            try:
                await self.owner.feed_task

            except Exception:
                pass

            finally:
                self.owner.feed_task = None

        if self.owner.stream_task:
            try:
                self.owner.stream_task = None

                if not silent:
                    Log.broadcast("Stream closed")

            except Exception as e:
                if not silent:
                    Log.error(f"Error closing stream: {e}")

            finally:
                self.owner.stream_task = None


        if self.owner.piwave:
            try:
                self.owner.piwave.cleanup()  # stops AND cleanups

            except Exception as e:
                if not silent:
                    Log.error(f"Error stopping PiWave: {e}")

            finally:
                self.owner.piwave = None

        self.owner.broadcasting = False
        self.owner.tips.is_broadcasting = False
        self.owner.broadcast_start_time = None
        self.owner.current_file = None

        if not silent:
            Log.broadcast("Stopped broadcast")
    

def setup(reg):
    reg.register(StopOp)