import asyncio
import hashlib
from pathlib import Path
import tempfile

from shared.env import Env
from shared.logger import Log
from shared.ops import CliOp
from shared.morser import text_to_morse

class MorseOp(CliOp):
    """
    The 'morse' command OP. Creates a morse .wav file into the
    server's tmp directory, uploads it to the targets, and starts it.

    Currently assumes the clients take 5 seconds to download the file,
    as our current systems don't allow efficient download tracking.

    No caching (such as SSTV caching) is implemented yet.
    """

    name = "morse"
    syntax = "<targets> <text|file> [wpm] [frequency] [loop] [ps] [rt] [pi]"

    async def handle(
        self,
        targets: list = [],
        text_src: str = None,
        wpm: int = 20,
        morse_freq: int = 700,
        frequency: float = 90.0,
        loop: bool = False,
        ps: str = "BotWave",
        rt: str = "Broadcasting",
        pi: str = "FFFF",
        is_cmd: bool = False,
        cmd_parts: list = []
    ):
        if is_cmd:
            targets, text_src, wpm, morse_freq, frequency, loop, ps, rt, pi = self.parse(cmd_parts)

            if not targets:
                return

            targets = self.owner.parse_targets(targets)

            if not targets:
                Log.warning("No client(s) found matching the query")
                return


        if Path(text_src).is_file():
            try:
                with open(text_src, "r", encoding="utf-8") as f:
                    text = f.read()

                Log.morse(f"Loaded Morse text from file: {text_src}")

            except Exception as e:
                Log.error(f"Failed to read text file: {e}")
                return 
            
        else:
            text = text_src

        morse_freq = Env.get_int("MORSE_FREQUENCY", 700)
        morse_sr = Env.get_int("MORSE_SAMPLE_RATE", 48000)
        output_wav = self.cache(text, morse_freq, morse_sr)

        if Path(output_wav).exists():
            Log.sstv(f"Using cached Morse WAV...")
            success = True

        else:
            Log.morse(f"Generating Morse WAV ({wpm} WPM @ {morse_freq}Hz)...")
            success = text_to_morse(text=text, filename=output_wav, wpm=wpm, frequency=morse_freq, sample_rate=morse_sr)

        if not success or not Path(output_wav).exists():
            Log.error("Failed to generate Morse WAV")
            return

        if is_cmd:
            self.owner.queue.manual_pause()

        Log.morse(f"Uploading {output_wav} to {len(targets)} clients...")
        await self.registry.dispatch("upload", targets=targets, file=output_wav)
        await asyncio.sleep(5)

        Path(output_wav).unlink()

        await self.registry.dispatch(
            "start",
            targets=targets,
            file=Path(output_wav).name,
            frequency=frequency,
            loop=loop,
            ps=ps,
            rt=rt,
            pi=pi,
        )

    def cache(self, text, freq, rate):
        key = f"{text}|{freq}|{rate}"
        digest = hashlib.sha256(key.encode()).hexdigest()[:16]

        cache_dir = Path(tempfile.gettempdir()) / "bw_morse"
        cache_dir.mkdir(parents=True, exist_ok=True)

        # including morse_ prefix on server because it'll end into the clients upload folder
        return str(cache_dir / f"morse_{digest}.wav") 

    def parse(self, cmd_parts):
        if len(cmd_parts) < 2:
            Log.error("Usage: morse <targets> <text|file> [wpm] [frequency] [loop] [ps] [rt] [pi]")
            return (None, None, None, None, None, None, None, None, None)

        targets = cmd_parts[0]
        text_src = cmd_parts[1]
        wpm = int(cmd_parts[2]) if len(cmd_parts) > 2 else Env.get_int("DEFAULT_MORSE_WPM", 20)
        morse_freq = Env.get_int("MORSE_FREQUENCY", 700)
        frequency = float(cmd_parts[3]) if len(cmd_parts) > 3 else Env.get_float("DEFAULT_FREQ", 90)
        loop = cmd_parts[4].lower() == 'true' if len(cmd_parts) > 4 else False
        ps = cmd_parts[5] if len(cmd_parts) > 5 else Env.get("DEFAULT_PS", "BotWave")
        rt = cmd_parts[6] if len(cmd_parts) > 6 else Env.get("DEFAULT_RT", "Morse")
        pi = cmd_parts[7] if len(cmd_parts) > 7 else Env.get("DEFAULT_PI", "FFFF")

        return (targets, text_src, wpm, morse_freq, frequency, loop, ps, rt, pi)


def setup(reg):
    reg.register(MorseOp)