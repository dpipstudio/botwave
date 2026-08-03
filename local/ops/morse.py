from pathlib import Path
import uuid

from shared.env import Env
from shared.logger import Log
from shared.morser import text_to_morse
from shared.ops import CliOp

class MorseOp(CliOp):
    name = "morse"
    syntax = "<text|file> [wpm] [frequency] [loop] [ps] [rt] [pi]"

    async def handle(self, text_src: str = None, wpm: int = 700, frequency: float = 90.0, loop: bool = False, ps: str = "BotWave", rt: str = "Broadcasting", pi: str = "FFFF", is_cmd: bool = False, cmd_parts: list = []):
        if is_cmd:
            text_src, wpm, frequency, loop, ps, rt, pi = self.parse(cmd_parts)

            if not text_src:
                return

            text_path = Path(text_src)

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

        output_wav = str(Path(Env.get("UPLOAD_DIR")) / f"morse_{uuid.uuid4().hex[:8]}.wav")
        morse_freq = Env.get_int("MORSE_FREQUENCY", 700)
        morse_sr = Env.get_int("MORSE_SAMPLE_RATE", 48000)

        Log.morse(f"Generating Morse WAV ({wpm} WPM @ {morse_freq}Hz)...")
        success = text_to_morse(text=text, filename=output_wav, wpm=wpm, frequency=morse_freq, sample_rate=morse_sr)

        if not success or not Path(output_wav).exists():
            Log.error("Failed to generate Morse WAV")
            return

        Log.morse(f"Broadcasting {output_wav}...")
        await self.registry.dispatch(
            "start",
            file_path=output_wav,
            frequency=frequency,
            ps=ps,
            rt=rt,
            pi=pi,
            loop=loop
            )



    def parse(self, cmd_parts):
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


def setup(reg):
    reg.register(MorseOp)