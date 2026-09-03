import hashlib
import tempfile
from pathlib import Path
from typing import Any

from shared.env import Env
from shared.logger import Log
from shared.morser import text_to_morse
from shared.ops import CliOp

class MorseOp(CliOp):
    """
    The 'morse' command OP. Creates a morse .wav file and then
    starts it using the "start" command.

    The generated Morse files are cached under <tmp_dir>/bw_morse/morse_<hash>.wav.
    """

    name = "morse"
    syntax = "<text|file> [wpm] [frequency] [loop] [ps] [rt] [pi]"
    short_help = "Convert text to morse code and broadcast it"
    long_help = """\
Convert text to morse code and broadcast it.
If the first argument is a <file>, read its content and
convert it. If not, use the <text> itself.

Generated .wav files are available into '/tmp/bw_morse/'.

Other positional arguments:
[wpm]: Words per minute to generate
[frequency]: The frequency to broadcast to.
[loop]: If the audio should be looped
[ps]: Program Service, max. 8 chars
[rt]: Radio Text, max 64 chars
[pi]: Program Identifier, 4 hex chars
"""
    examples = [
        "morse file.txt",
        "morse 'Hello, world!' 20 96.9 true 'BotWave'"
    ]
    env_vars = {
        "MORSE_FREQUENCY": ("700", "The audio frequency to generate the morse tone with"),
        "MORSE_SAMPLE_RATE": ("48000", "The sample rate to generate the .wav file with"),
        "BACKEND_PATH": ("bw_custom", "The path to the broadcast backend"),
        "BACKEND_BYPASS_CACHE": ("false", "If the backend manager should discard its cached backend path"),
        "SKIP_CHECKS": ("false", "If the backend manager should skip its own system requirements checks"),
        "DEFAULT_MORSE_WPM": ("20", "The default morse words per minute"),
        "DEFAULT_FREQ": ("90", "The default frequency to broadcast to"),
        "DEFAULT_PS": ("BotWave", "The default program service"),
        "DEFAULT_RT": ("Morse", "The default radio text"),
        "DEFAULT_PI": ("FFFF", "The default program identifier")
    }

    async def handle(
        self,
        text_src: str = "",
        wpm: int = 20,
        frequency: float = 90.0,
        loop: bool = False,
        ps: str = "BotWave",
        rt: str = "Broadcasting",
        pi: str = "FFFF",
        is_cmd: bool = False,
        cmd_parts: list[str] = []
    ):
        if is_cmd:
            text_src, wpm, frequency, loop, ps, rt, pi = self.parse(cmd_parts)

            if not text_src:
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
            Log.morse(f"Using cached Morse WAV...")
            success = True

        else:
            Log.morse(f"Generating Morse WAV ({wpm} WPM @ {morse_freq}Hz)...")
            success = text_to_morse(text=text, filename=output_wav, wpm=wpm, frequency=morse_freq, sample_rate=morse_sr)

        if not success or not Path(output_wav).exists():
            Log.error("Failed to generate Morse WAV")
            return

        if is_cmd:
            self.owner.queue.manual_pause()

        Log.morse(f"Broadcasting {output_wav}...")
        await self.registry.dispatch(
            "start",
            file=output_wav,
            frequency=frequency,
            ps=ps,
            rt=rt,
            pi=pi,
            loop=loop
            )

    def cache(self, text: str, freq: int, rate: int):
        key = f"{text}|{freq}|{rate}"
        digest = hashlib.sha256(key.encode()).hexdigest()[:16]

        cache_dir = Path(tempfile.gettempdir()) / "bw_morse"
        cache_dir.mkdir(parents=True, exist_ok=True)

        return str(cache_dir / f"{digest}.wav")


    def parse(self, cmd_parts: list[str]) -> tuple[Any, ...]:
        if len(cmd_parts) < 1:
            Log.error("Usage: morse <text|file> [wpm] [frequency] [loop] [ps] [rt] [pi]")
            return (None, None, None, None, None, None, None)

        text_src = cmd_parts[0]
        wpm = int(cmd_parts[1]) if len(cmd_parts) > 1 else Env.get_int("DEFAULT_MORSE_WPM", 20)
        frequency = float(cmd_parts[2]) if len(cmd_parts) > 2 else Env.get_float("DEFAULT_FREQ", 90)
        loop = cmd_parts[3].lower() == 'true' if len(cmd_parts) > 3 else False
        ps = cmd_parts[4] if len(cmd_parts) > 4 else Env.get("DEFAULT_PS", "BotWave")
        rt = cmd_parts[5] if len(cmd_parts) > 5 else Env.get("DEFAULT_RT", "Morse")
        pi = cmd_parts[6] if len(cmd_parts) > 6 else Env.get("DEFAULT_PI", "FFFF")
                
        return (text_src, wpm, frequency, loop, ps, rt, pi)


def setup(reg: Any):
    reg.register(MorseOp)