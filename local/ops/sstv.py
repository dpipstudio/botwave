import hashlib
import tempfile
from pathlib import Path
from typing import Any

from shared.env import Env
from shared.logger import Log
from shared.ops import CliOp
from shared.sstv import make_sstv_wav

class SSTVOp(CliOp):
    """
    The 'sstv' command OP. Creates a SSTV .wav file into a
    tmp directory, and starts it using the 'start' command.

    The generated SSTV files are cached under <tmp_dir>/bw_sstv/<hash>.wav.
    """

    name = "sstv"
    syntax = "<image_path> [mode] [frequency] [loop] [ps] [rt] [pi]"
    short_help = "Convert an image into SSTV audio and broadcast it"
    long_help = """\
Convert an <image> into SSTV audio and broadcast it.
If [mode] is not specified, automatically selects the best
mode available.

Available modes: MartinM1, MartinM2, ScottieS1, ScottieS2,
ScottieDX, Robot36, PasokonP3, PasokonP5, PasokonP7, PD90,
PD120, PD160, PD180, PD240, PD290, WraaseSC2120, WraaseSC2180,
Robot8BW, Robot24BW

Generated .wav files are available into '/tmp/bw_sstv/'.

Other positional arguments:
[loop]: If the audio should be looped
[ps]: Program Service, max. 8 chars
[rt]: Radio Text, max 64 chars
[pi]: Program Identifier, 4 hex chars
"""
    examples = [
        "sstv image.png",
        "sstv image.png Robot36 96.9 true 'BotWave'"
    ]
    env_vars = {
        "SSTV_SAMPLE_RATE": ("48000", "The sample rate to generate the .wav file with"),
        "BACKEND_PATH": ("bw_custom", "The path to the broadcast backend"),
        "BACKEND_BYPASS_CACHE": ("false", "If the backend manager should discard its cached backend path"),
        "SKIP_CHECKS": ("false", "If the backend manager should skip its own system requirements checks"),
        "SSTV_DEFAULT_MODE": ("auto", "The default SSTV mode"),
        "DEFAULT_FREQ": ("90", "The default frequency to broadcast to"),
        "DEFAULT_PS": ("BotWave", "The default program service"),
        "DEFAULT_RT": ("<image filename>", "The default radio text"),
        "DEFAULT_PI": ("FFFF", "The default program identifier")
    }

    async def handle(
        self,
        img_path: str = "",
        mode: str = "",
        frequency: float = 90.0,
        loop: bool = False,
        ps: str = "BotWave",
        rt: str = "Broadcasting",
        pi: str = "FFFF",
        is_cmd: bool = False,
        cmd_parts: list[str] = []
        ):
        if is_cmd:
            img_path, mode, frequency, loop, ps, rt, pi = self.parse(cmd_parts)

            if not img_path:
                return

        if not Path(img_path).is_file():
            Log.error(f"Image file {img_path} not found")
            return

        output_wav = self.cache(img_path, mode)

        if Path(output_wav).is_file():
            Log.sstv(f"Using cached SSTV WAV for {img_path}...")
            success = True

        else:
            Log.sstv(f"Generating SSTV WAV from {img_path} using mode {mode or 'auto'}...")
            success = make_sstv_wav(img_path, output_wav, mode)

        if success:
            if is_cmd:
                self.owner.queue.manual_pause()

            await self.registry.dispatch(
                "start",
                file=output_wav,
                frequency=frequency,
                ps=ps,
                rt=rt,
                pi=pi,
                loop=loop
                )

        else:
            Log.error("Failed to generate SSTV")


    def parse(self, cmd_parts: list[str]) -> tuple[Any, ...]:
        if len(cmd_parts) < 1:
            Log.error("Usage: sstv <image_path> [mode] [frequency] [loop] [ps] [rt] [pi]")
            return (None, None, None, None, None, None, None)
        
        img_path = cmd_parts[0]
        mode = cmd_parts[1] if len(cmd_parts) > 1 else None

        frequency = float(cmd_parts[2]) if len(cmd_parts) > 2 else Env.get_float("DEFAULT_FREQ", 90)
        loop = cmd_parts[3].lower() == 'true' if len(cmd_parts) > 3 else False
        ps = cmd_parts[4] if len(cmd_parts) > 4 else Env.get("DEFAULT_PS", "BotWave")
        rt = cmd_parts[5] if len(cmd_parts) > 5 else Env.get("DEFAULT_RT", Path(img_path).name)
        pi = cmd_parts[6] if len(cmd_parts) > 6 else Env.get("DEFAULT_PI", "FFFF")

        return (img_path, mode, frequency, loop, ps, rt, pi)

    def cache(self, img_path: str, mode: str):
        # cache key includes mtime so editing the image busts the cache automatically
        abs_path = Path(img_path).resolve()
        mtime = abs_path.stat().st_mtime
        key = f"{abs_path}|{mode or 'auto'}|{mtime}"
        digest = hashlib.sha256(key.encode()).hexdigest()[:16]

        cache_dir = Path(tempfile.gettempdir()) / "bw_sstv"
        cache_dir.mkdir(parents=True, exist_ok=True)

        return str(cache_dir / f"{digest}.wav")

def setup(reg: Any):
    reg.register(SSTVOp)