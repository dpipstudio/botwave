from pathlib import Path
import morse_talk as mtalk
import wave

from shared.logger import Log

def morse_timings(wpm):
    dot = 1.2 / wpm
    dash = dot * 3
    intra_char = dot
    inter_char = dot * 3
    inter_word = dot * 7
    return dot, dash, intra_char, inter_char, inter_word

def tone(np, frequency, duration, sample_rate, volume=0.5):
    num_samples = int(sample_rate * duration)
    t = np.arange(num_samples, dtype=np.float64)
    return volume * np.sin(2 * np.pi * frequency * t / sample_rate)

def silence(np, duration, sample_rate):
    return np.zeros(int(sample_rate * duration), dtype=np.float64)

def text_to_morse(text, filename="output.wav", wpm=20, frequency=700, sample_rate=44100):
    try:
        import numpy as np

    except ImportError:
        parent_parent = Path(__file__).parent.parent
        pip_path = parent_parent / "venv" / "bin" / "pip"

        Log.morse("Please install required modules:")
        Log.morse(f"{pip_path} install numpy")
        return False

    try:
        Log.morse(f"Encoding {len(text)} characters to morse...")
        morse = mtalk.encode(text)

        dot, dash, intra, inter, word = morse_timings(wpm)
        chunks = []

        for char in morse:
            if char == ".":
                chunks.append(tone(np, frequency, dot, sample_rate))
                chunks.append(silence(np, intra, sample_rate))

            elif char == "-":
                chunks.append(tone(np, frequency, dash, sample_rate))
                chunks.append(silence(np, intra, sample_rate))

            elif char == " ":
                chunks.append(silence(np, inter, sample_rate))

            elif char == "\n":
                chunks.append(silence(np, word, sample_rate))

        # Tail silence so radios don't clip the end
        chunks.append(silence(np, word, sample_rate))

        # concatenate once and convert to 16-bit PCM in bulk, instead of
        # struct.pack()-ing and writeframes()-ing one sample at a time
        audio = np.concatenate(chunks) if chunks else np.zeros(0, dtype=np.float64)
        pcm = np.clip(audio * 32767, -32768, 32767).astype("<i2")

        with wave.open(filename, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(pcm.tobytes())

    except Exception as e:
        Log.error(f"Failed to encode to WAV: {e}")
        return False

    return True