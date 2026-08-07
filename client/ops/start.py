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

class StartOp(GeneralOp):
    """
    The OP handling Commands.START. Starts a broadcast by
    spawning a PiWave() instance and starting it with the
    provided settings.

    Also starts the piwave_monitor if not in loop mode.

    Note regarding the backends: PiWave has a backend cache,
    so updating the backend binary for a new one in 
    BACKEND_PATH might not work correctly the first time if
    BACKEND_BYPASS_CACHE isn't set to true.
    """

    commands = {Commands.START: "start"}

    async def start(self, parsed: dict):
        kwargs = parsed["kwargs"]
        filename = kwargs.get('filename')

        if not filename:
            await self.owner.proto.reply(
                parsed,
                Commands.ERROR,
                message="Missing filename"
            )
            return

        try:
            filename = PathValidator.sanitize_filename(filename)
            file_path = PathValidator.safe_join(Env.get("UPLOAD_DIR"), filename)

        except SecurityError as e:
            Log.error(f"Invalid filename from server: {e}")
            await self.owner.proto.reply(
                parsed,
                Commands.ERROR,
                message="Provided filename raised a security violation"
            )
            return

        if not Path(file_path).is_file():
            await self.owner.proto.reply(
                parsed,
                Commands.ERROR,
                message=f"File not found: {filename}"
            )
            return

        frequency = float(kwargs.get('frequency', Env.get_float("DEFAULT_FREQ", 90.0)))
        ps = kwargs.get('ps', Env.get("DEFAULT_PS", 'BotWave'))
        rt = kwargs.get('rt', Env.get("DEFAULT_RT", 'Broadcasting'))
        pi = kwargs.get('pi', Env.get("DEFAULT_PI", 'FFFF'))
        loop = kwargs.get('loop', 'false').lower() == 'true'
        start_at = float(kwargs.get('start_at', 0))

        if start_at > 0:
            current_time = datetime.now(timezone.utc).timestamp()
            if start_at > current_time:
                delay = start_at - current_time
                Log.broadcast(f"Scheduled start in {delay:.2f} seconds")

                asyncio.create_task(self.delay(
                    file_path, filename, frequency, ps, rt, pi, loop, delay
                ))

                await self.owner.proto.reply(
                    parsed,
                    Commands.OK,
                    message=f"Scheduled in {delay:.2f}s"
                )
                return

        started = await self.start_broadcast(file_path, filename, frequency, ps, rt, pi, loop)

        if isinstance(started, Exception):
            await self.owner.proto.reply(
                parsed,
                Commands.ERROR,
                message=str(started)
            )

        else:
            await self.owner.proto.reply(
                parsed,
                Commands.OK,
                message="Broadcast started"
            )

    async def delay(self, file_path, filename, frequency, ps, rt, pi, loop, delay):
        await asyncio.sleep(delay)
        started = await self.start_broadcast(file_path, filename, frequency, ps, rt, pi, loop)

        if isinstance(started, Exception):
            await self.owner.proto.fire(
                Commands.ERROR,
                message=str(started)
            )

        else:
            await self.owner.proto.fire(
                Commands.OK,
                message="Broadcast started"
            )


    async def start_broadcast(self, file_path, filename, frequency, ps, rt, pi, loop):
        async def finished():
            Log.info("Playback finished, stopping broadcast...")

            try:
                await self.owner.proto.fire(
                    Commands.END,
                    filename=filename
                )
            except Exception as e:
                Log.error(f"Error notifying server of broadcast end: {e}")

            await self.registry.dispatch("stop_broadcast", silent=True)

        if self.owner.broadcasting:
            await self.registry.dispatch("stop_broadcast", silent=True)

        try:
            backend_name = Path(Env.get("BACKEND_PATH", "bw_custom")).name
            talk = Env.get_bool("TALK")

            backend_classes[backend_name] = BWCustom

            self.owner.piwave = PiWave(
                frequency=frequency,
                ps=ps,
                rt=rt,
                pi=pi,
                loop=loop,
                backend=backend_name,
                debug=talk,
                silent=not talk,
                force_search=Env.get_bool("BACKEND_BYPASS_CACHE"),
                unsafe=Env.get_bool("SKIP_CHECKS")
            )

            success = self.owner.piwave.play(file_path, blocking=False)

            if not loop:
                self.owner.piwave_monitor.start(self.owner.piwave, finished, asyncio.get_event_loop())

            if success:
                Log.broadcast(f"Currently broadcasting {filename} on {frequency} MHz")
                self.owner.broadcast_start_time = time.time()
                self.owner.tips.is_broadcasting = True
                self.owner.broadcasting = True
                self.owner.current_file = filename

            else:
                raise Exception("PiWave returned a non-true status, set talk to true to debug.")
            
            return True

        except Exception as e:
            Log.error(f"Broadcast error: {e}")
            self.owner.broadcasting = False
            self.owner.tips.is_broadcasting = False
            self.owner.broadcast_start_time = None
            return e

def setup(reg):
    reg.register(StartOp)