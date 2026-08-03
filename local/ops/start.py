import os
from pathlib import Path
from piwave import PiWave
from piwave.backends import backend_classes
import time

from shared.bw_custom import BWCustom
from shared.env import Env
from shared.logger import Log
from shared.ops import CliOp

class StartOp(CliOp):
    name = "start"
    syntax = "<file> [freq] [loop] [ps] [rt] [pi]"

    async def handle(self, file_path: str = None, frequency: float = 90.0, ps: str = "BotWave", rt: str = "Broadcasting", pi: str = "FFFF", loop: bool = False, is_cmd: bool = False, cmd_parts: list = []):
        if is_cmd:
            file_path, frequency, ps, rt, pi, loop = self.parse(cmd_parts)

            if not file_path:
                return

        if not os.path.exists(file_path):
            Log.error(f"File {file_path} not found")
            return
        
        if is_cmd:
            self.owner.queue.manual_pause()
        
        if self.owner.broadcasting:
            await self.registry.dispatch("stop")

        backend_name = Path(Env.get("BACKEND_PATH", "bw_custom")).name
        silent = not Env.get_bool("TALK")

        try:
            backend_classes[backend_name] = BWCustom

            self.owner.piwave = PiWave(
                frequency=frequency,
                ps=ps,
                rt=rt,
                pi=pi,
                loop=loop,
                backend=backend_name,
                debug=not silent,
                silent=silent,
                force_search=Env.get_bool("BACKEND_BYPASS_CACHE"),
                unsafe=Env.get_bool("SKIP_CHECKS")
            )

            self.owner.current_file = file_path
            self.owner.broadcasting = True
            success = self.owner.piwave.play(file_path)

            
            if success:
                Log.success(f"Started broadcasting {file_path} on {frequency}MHz")
                self.owner.broadcast_start_time = time.time()

                await self.registry.dispatch("handlers_onstart", context={"BW_BROADCAST_FILE": file_path, "BW_BROADCAST_FREQ": str(frequency)})

                if not loop:
                    async def finished():
                        Log.info("Playback finished, stopping broadcast...")
                        await self.registry.dispatch("stop", silent=True)
                        self.owner.queue.on_broadcast_ended()

                    self.owner.piwave_monitor.start(self.owner.piwave, finished)

                return

            else:
                Log.error("PiWave returned a non-true status, set talk to true to debug.")

            return
        
        except Exception as e:
            Log.error(f"Error starting broadcast: {e}")
            self.owner.broadcasting = False
            self.owner.broadcast_start_time = None
            self.owner.current_file = None
            self.owner.piwave = None
            return

    def parse(self, cmd_parts):
        if len(cmd_parts) < 1:
            Log.error("Usage: start <file> [frequency] [loop] [ps] [rt] [pi]")
            return (None, None, None, None, None, None)
        
        file_path = os.path.join(Env.get("UPLOAD_DIR"), cmd_parts[0])
        frequency = float(cmd_parts[1]) if len(cmd_parts) > 1 else Env.get_float("DEFAULT_FREQ", 90)
        loop = cmd_parts[2].lower() == 'true' if len(cmd_parts) > 2 else False
        ps = cmd_parts[3] if len(cmd_parts) > 3 else Env.get("DEFAULT_PS", "BotWave")
        rt = cmd_parts[4] if len(cmd_parts) > 4 else Env.get("DEFAULT_RT", cmd_parts[0])
        pi = cmd_parts[5] if len(cmd_parts) > 5 else Env.get("DEFAULT_PI", "FFFF")

        return (file_path, frequency, ps, rt, pi, loop)

def setup(reg):
    reg.register(StartOp)