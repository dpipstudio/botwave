import morse_talk as mtalk
import wave
import struct
import math
from logger import Log

def morse_timings(wpm):
    dot = 1.2 / wpm
    dash = dot * 3
    intra_char = dot
    inter_char = dot * 3
    inter_word = dot * 7
    return dot, dash, intra_char, inter_char, inter_word

def tone(frequency, duration, sample_rate, volume=0.5):
    num_samples = int(sample_rate * duration)
    return [
        volume * math.sin(2 * math.pi * frequency * t / sample_rate)
        for t in range(num_samples)
    ]

def silence(duration, sample_rate):
    return [0.0] * int(sample_rate * duration)

def text_to_morse(text, filename="output.wav", wpm=20, frequency=700, sample_rate=44100):
    try:
        Log.morse(f"Encoding {len(text)} characters to morse...")
        morse = mtalk.encode(text)

        dot, dash, intra, inter, word = morse_timings(wpm)
        audio = []

        for char in morse:
            if char == ".":
                audio += tone(frequency, dot, sample_rate)
                audio += silence(intra, sample_rate)

            elif char == "-":
                audio += tone(frequency, dash, sample_rate)
                audio += silence(intra, sample_rate)

            elif char == " ":
                audio += silence(inter, sample_rate)

            elif char == "\n":
                audio += silence(word, sample_rate)

        # Tail silence so radios don't clip the end
        audio += silence(word, sample_rate)

        with wave.open(filename, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)

            for sample in audio:
                wf.writeframes(struct.pack("<h", int(sample * 32767)))

    except Exception as e:
        Log.error(f"Failed to encode to WAV: {e}")
        return False

    return True
