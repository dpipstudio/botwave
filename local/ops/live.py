import os
from pathlib import Path
from piwave import PiWave
from piwave.backends import backend_classes
import time

from shared.bw_custom import BWCustom
from shared.env import Env
from shared.logger import Log
from shared.ops import CliOp

class LiveOp(CliOp):
    name = "live"
    syntax = "[freq] [ps] [rt] [pi]"

    async def handle(self, frequency: float = 90.0, ps: str = "BotWave", rt: str = "Broadcasting", pi: str = "FFFF", is_cmd: bool = False, cmd_parts: list = []):
        if is_cmd:
            frequency, ps, rt, pi = self.parse(cmd_parts)

        if not self.owner.alsa.is_supported():
            Log.alsa("Live broadcast is not supported on this installation.")
            Log.alsa("Did you setup the ALSA loopback card correctly ?")
            return

        if is_cmd:
            self.owner.queue.manual_pause()
        
        if self.owner.broadcasting:
            await self.owner.registry.dispatch("stop")

        backend_name = Path(Env.get("BACKEND_PATH", "bw_custom")).name
        silent = not Env.get_bool("TALK")

        try:
            backend_classes[backend_name] = BWCustom

            self.piwave = PiWave(
                frequency=frequency,
                ps=ps,
                rt=rt,
                pi=pi,
                backend=backend_name,
                debug=not silent,
                silent=silent,
                force_search=Env.get_bool("BACKEND_BYPASS_CACHE"),
                unsafe=Env.get_bool("SKIP_CHECKS")
            )

            self.owner.alsa.start()

            audio_queue = self.owner.alsa.subscribe()

            self.owner.current_file = "live_playback"
            self.owner.broadcasting = True

            success = self.piwave.play(
                self.owner.alsa.audio_generator(audio_queue),
                sample_rate=self.owner.alsa.rate,
                channels=self.owner.alsa.channels,
                chunk_size=self.owner.alsa.period_size
            )

            if success:
                Log.success(f"Live broadcast started on {frequency}MHz")
                self.owner.broadcast_start_time = time.time()

                #TODO: self.owner.registry.dispatch("handlers_onstart", context={**self._build_context(), "BW_BROADCAST_FREQ": str(frequency)})
                await self.owner.registry.dispatch("handlers_onstart", context={"BW_BROADCAST_FREQ": str(frequency)})

                card = Env.get("ALSA_CARD", 'BotWave')
                Log.alsa(f"To play live, please set your output sound card (ALSA) to '{card}'.")
                Log.alsa(f"We're expecting {self.owner.alsa.rate}kHz on {self.owner.alsa.channels} channels.")
                return

            else:
                Log.error("PiWave returned a non-true status, set talk to true to debug.")

            return
        
        except Exception as e:
            Log.error(f"Error starting broadcast: {e}")
            self.owner.alsa.stop()
            self.owner.broadcasting = False
            self.owner.broadcast_start_time = None
            self.owner.current_file = None
            self.owner.piwave = None
            return

    def parse(self, cmd_parts):
        frequency = float(cmd_parts[0]) if len(cmd_parts) > 1 else Env.get_float("DEFAULT_FREQ", 90)
        ps = cmd_parts[2] if len(cmd_parts) > 2 else Env.get("DEFAULT_PS", "BotWave")
        rt = cmd_parts[3] if len(cmd_parts) > 3 else Env.get("DEFAULT_RT", "Live")  # Fixed index and fallback
        pi = cmd_parts[4] if len(cmd_parts) > 4 else Env.get("DEFAULT_PI", "FFFF")  # Fixed index

        return (frequency, ps, rt, pi)