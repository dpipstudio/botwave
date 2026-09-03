import asyncio
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
    The 'sstv' command OP.  Creates a SSTV .wav file into the
    server's tmp directory, uploads it to the targets, and starts it.

    Currently assumes the clients take 5 seconds to download the file,
    as our current systems don't allow efficient download tracking.

    The generated SSTV files are cached under <tmp_dir>/bw_sstv/<hash>.wav.
    """

    name = "sstv"
    syntax = "<targets> <image_path> [mode] [frequency] [loop] [ps] [rt] [pi]"
    short_help = "Convert an image into SSTV audio and broadcast it on client(s)"
    long_help = """\
Convert an <image_path> into SSTV audio, upload the
resulting WAV to <targets>, and broadcast it.
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
        "sstv all mycat.png",
        "sstv all mycat.png Robot36 90 false 'My Cat!' 'PsPs Cutie' FFFF"
    ]
    env_vars = {
        "SSTV_SAMPLE_RATE": ("48000", "The sample rate to generate the .wav file with"),
        "SSTV_DEFAULT_MODE": ("auto", "The default SSTV mode"),
        "DEFAULT_FREQ": ("90", "The default frequency to broadcast to"),
        "DEFAULT_PS": ("BotWave", "The default program service"),
        "DEFAULT_RT": ("<image filename>", "The default radio text"),
        "DEFAULT_PI": ("FFFF", "The default program identifier")
    }
    async def handle(
        self,
        targets: list[str] = [],
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
            targets, img_path, mode, frequency, loop, ps, rt, pi = self.parse(cmd_parts)

            if not targets:
                return

            targets = self.owner.parse_targets(targets)

            if not targets:
                Log.warning("No client(s) found matching the query")
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
            Log.sstv(f"Uploading {output_wav} to {len(targets)} clients...")

            await self.registry.dispatch("upload", targets=targets, file=output_wav)
            await asyncio.sleep(5 * len(targets))  # Wait for upload

            if is_cmd:
                self.owner.queue.manual_pause()

            await self.registry.dispatch(
                "start",
                targets=targets,
                file=Path(output_wav).name,
                frequency=frequency,
                ps=ps,
                rt=rt,
                pi=pi,
                loop=loop
                )

        else:
            Log.error("Failed to generate SSTV")

    def parse(self, cmd_parts: list[str]) -> tuple[Any, ...]:
        if len(cmd_parts) < 2:
            Log.error("Usage: sstv <targets> <image_path> [mode] [frequency] [loop] [ps] [rt] [pi]")
            return (None, None, None, None, None, None, None, None)

        targets = cmd_parts[0]
        img_path = cmd_parts[1]
        mode = cmd_parts[2] if len(cmd_parts) > 2 else None
        frequency = float(cmd_parts[3]) if len(cmd_parts) > 3 else Env.get_float("DEFAULT_FREQ", 90)
        loop = cmd_parts[4].lower() == 'true' if len(cmd_parts) > 4 else False
        ps = cmd_parts[5] if len(cmd_parts) > 5 else Env.get("DEFAULT_PS", "BotWave")
        rt = cmd_parts[6] if len(cmd_parts) > 6 else Env.get("DEFAULT_RT", Path(img_path).name)
        pi = cmd_parts[7] if len(cmd_parts) > 7 else Env.get("DEFAULT_PI", "FFFF")

        return (targets, img_path, mode, frequency, loop, ps, rt, pi)

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