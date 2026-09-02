import os
import time
from pathlib import Path
from piwave import PiWave
from piwave.backends import backend_classes
from typing import Any

from shared.bw_custom import BWCustom
from shared.dirutils import BW_PATH
from shared.env import Env
from shared.logger import Log
from shared.ops import CliOp

class StartOp(CliOp):
    """
    The 'start' command OP. Starts a broadcast by spawning
    a PiWave() instance and starting it.

    Also starts the piwave_monitor if we aren't looping.

    Note regarding the backends: PiWave has a backend cache,
    so updating the backend binary for a new one in 
    BACKEND_PATH might not work correctly the first time if
    BACKEND_BYPASS_CACHE isnt set to true.
    """

    name = "start"
    syntax = "<file> [frequency] [loop] [ps] [rt] [pi]"
    short_help = "Start broadcasting a WAV file"
    long_help = """\
Start broadcasting a wav file from the upload
directory on [frequency].

Other positional arguments:
[loop]: If the audio should be looped
[ps]: Program Service, max. 8 chars
[rt]: Radio Text, max 64 chars
[pi]: Program Identifier, 4 hex chars
"""
    env_vars = {
        "UPLOAD_DIR": (f"{BW_PATH}/uploads", "The upload directory to retrieve the file from"),
        "BACKEND_PATH": ("bw_custom", "The path to the broadcast backend"),
        "BACKEND_BYPASS_CACHE": ("false", "If the backend manager should discard its cached backend path"),
        "SKIP_CHECKS": ("false", "If the backend manager should skip its own system requirements checks"),
        "DEFAULT_FREQ": ("90", "The default frequency to broadcast to"),
        "DEFAULT_PS": ("BotWave", "The default program service"),
        "DEFAULT_RT": ("Live", "The default radio text"),
        "DEFAULT_PI": ("FFFF", "The default program identifier")
    }

    async def handle(
        self,
        file: str = "",
        frequency: float = 90.0,
        ps: str = "BotWave",
        rt: str = "Broadcasting",
        pi: str = "FFFF",
        loop: bool = False,
        is_cmd: bool = False,
        cmd_parts: list[str] = []
    ):
        if is_cmd:
            file, frequency, ps, rt, pi, loop = self.parse(cmd_parts)

            if not file:
                return

        if not os.path.exists(file):
            Log.error(f"File {file} not found")
            return
        
        if is_cmd:
            self.owner.queue.manual_pause()
        
        if self.owner.broadcasting:
            await self.registry.dispatch("stop")

        backend_name = Path(Env.get("BACKEND_PATH", "bw_custom")).name
        silent = not Env.get_bool("TALK")

        try:
            backend_classes[backend_name] = BWCustom # pyright: ignore

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

            self.owner.current_file = file
            self.owner.broadcasting = True
            self.owner.tips.is_broadcasting = True
            success = self.owner.piwave.play(file)

            
            if success:
                Log.success(f"Started broadcasting {file} on {frequency}MHz")
                self.owner.broadcast_start_time = time.time()

                await self.registry.dispatch("handlers_onstart", context={"BW_BROADCAST_FILE": file, "BW_BROADCAST_FREQ": str(frequency)})

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
            self.owner.tips.is_broadcasting = False
            self.owner.broadcast_start_time = None
            self.owner.current_file = None
            self.owner.piwave = None
            return

    def parse(self, cmd_parts: list[str]) -> tuple[Any, ...]:
        if len(cmd_parts) < 1:
            Log.error("Usage: start <file> [frequency] [loop] [ps] [rt] [pi]")
            return (None, None, None, None, None, None)
        
        file = os.path.join(Env.get("UPLOAD_DIR"), cmd_parts[0])
        frequency = float(cmd_parts[1]) if len(cmd_parts) > 1 else Env.get_float("DEFAULT_FREQ", 90)
        loop = cmd_parts[2].lower() == 'true' if len(cmd_parts) > 2 else False
        ps = cmd_parts[3] if len(cmd_parts) > 3 else Env.get("DEFAULT_PS", "BotWave")
        rt = cmd_parts[4] if len(cmd_parts) > 4 else Env.get("DEFAULT_RT", cmd_parts[0])
        pi = cmd_parts[5] if len(cmd_parts) > 5 else Env.get("DEFAULT_PI", "FFFF")

        return (file, frequency, ps, rt, pi, loop)

def setup(reg: Any):
    reg.register(StartOp)