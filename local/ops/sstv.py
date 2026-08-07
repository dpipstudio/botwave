import hashlib
from pathlib import Path
import tempfile

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

    async def handle(self, img_path: str = None, mode: str = None, frequency: float = 90.0, loop: bool = False, ps: str = "BotWave", rt: str = "Broadcasting", pi: str = "FFFF", is_cmd: bool = False, cmd_parts: list = []):
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


    def parse(self, cmd_parts):
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

    def cache(self, img_path, mode):
        # cache key includes mtime so editing the image busts the cache automatically
        abs_path = Path(img_path).resolve()
        mtime = abs_path.stat().st_mtime
        key = f"{abs_path}|{mode or 'auto'}|{mtime}"
        digest = hashlib.sha256(key.encode()).hexdigest()[:16]

        cache_dir = Path(tempfile.gettempdir()) / "bw_sstv"
        cache_dir.mkdir(parents=True, exist_ok=True)

        return str(cache_dir / f"{digest}.wav")

def setup(reg):
    reg.register(SSTVOp)