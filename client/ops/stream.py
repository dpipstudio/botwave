import asyncio
from pathlib import Path
from piwave import PiWave
from piwave.backends import backend_classes
import queue
import time

from shared.bw_custom import BWCustom
from shared.env import Env
from shared.logger import Log
from shared.ops import GeneralOp
from shared.protocol import Commands

class StreamOp(GeneralOp):
    """
    The OP handling Commands.STREAM_TOKEN. Starts a live
    broadcast by pulling PCM audio from the server via an
    HTTP stream and feeding it into a new PiWave() instance.
    """

    commands = {Commands.STREAM_TOKEN: "stream"}

    async def stream(self, parsed):
        kwargs = parsed["kwargs"]

        token = kwargs.get('token')
        rate = int(kwargs.get('rate', self.owner.alsa.rate))
        channels = int(kwargs.get('channels', self.owner.alsa.channels))

        # Broadcast params
        frequency = float(kwargs.get('frequency', Env.get_float("DEFAULT_FREQ", 90)))
        ps = kwargs.get('ps', Env.get("DEFAULT_PS", 'BotWave'))
        rt = kwargs.get('rt', Env.get("DEFAULT_RT", 'Streaming'))
        pi = kwargs.get('pi', Env.get("DEFAULT_PI", 'FFFF'))

        if not token:
            await self.owner.proto.reply(
                parsed,
                Commands.ERROR,
                message="Missing token"
            )
            return

        Log.broadcast(f"Received stream token (rate={rate}, channels={channels})")

        started = await self.start_stream(token, rate, channels, frequency, ps, rt, pi)

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
                message="Stream broadcast started"
            )


    async def start_stream(self, token, rate, channels, frequency, ps, rt, pi):
        async def finished():
            Log.info("Stream finished, stopping broadcast...")
            await self.registry.dispatch("stop_broadcast", silent=True)

        if self.owner.broadcasting:
            await self.registry.dispatch("stop_broadcast")

        try:
            backend_name = Path(Env.get("BACKEND_PATH", "bw_custom")).name
            talk = Env.get_bool("TALK")

            backend_classes[backend_name] = BWCustom

            self.owner.piwave = PiWave(
                frequency=frequency,
                ps=ps,
                rt=rt,
                pi=pi,
                loop=False,
                backend=backend_name,
                debug=talk,
                silent=not talk,
                force_search=Env.get_bool("BACKEND_BYPASS_CACHE"),
                unsafe=Env.get_bool("SKIP_CHECKS")
            )

            self.owner.stream_task = self.owner.http_client.stream_pcm_generator(
                server_host=Env.get("FHOST"),
                server_port=Env.get_int("FPORT"),
                token=token,
                rate=rate,
                channels=channels,
                chunk_size=1024
            )
            captured = self.owner.stream_task
            self.owner.stream_active = True

            stream_queue = queue.Queue(maxsize=50)

            if self.owner.feed_task and not self.owner.feed_task.done():
                self.owner.feed_task.cancel()
                try:
                    await self.owner.feed_task
                except asyncio.CancelledError:
                    pass

            self.owner.feed_task = asyncio.get_event_loop().create_task(self.feed_queue(captured, stream_queue))

            def sync_generator_wrapper():
                try:
                    while self.owner.stream_active:
                        try:
                            chunk = stream_queue.get(timeout=5)
                            if chunk is None:
                                break

                            yield chunk

                        except queue.Empty:
                            Log.warning("Stream stalled (queue timeout)")
                            break

                except GeneratorExit:
                    pass

                finally:
                    self.owner.stream_active = False

            success = self.owner.piwave.play(
                sync_generator_wrapper(),
                sample_rate=rate,
                channels=channels,
                chunk_size=1024
            )

            self.owner.piwave_monitor.start(self.owner.piwave, finished, asyncio.get_event_loop())

            if success:
                Log.broadcast(f"Broadcasting stream on {frequency} MHz (rate={rate}, channels={channels})")
                self.owner.broadcast_start_time = time.time()
                self.owner.tips.is_broadcasting = True
                self.owner.broadcasting = True
                self.owner.current_file = f"stream:{token[:8]}"

            else:
                raise Exception("PiWave returned a non-true status, set talk to true to debug.")

            return True

        except Exception as e:
            Log.error(f"Stream broadcast error: {e}")
            self.owner.broadcasting = False
            self.owner.tips.is_broadcasting = False
            self.owner.broadcast_start_time = None
            return e

    async def feed_queue(self, captured, stream_queue):
        try:
            async for chunk in captured:
                if not self.owner.stream_active:
                    break

                stream_queue.put(chunk)

        except Exception as e:
            Log.error(f"Stream feed error: {e}")
            
        finally:
            stream_queue.put(None)  # sentinel


def setup(reg):
    reg.register(StreamOp)