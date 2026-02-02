import subprocess
import os

from shared.logger import Log

SUPPORTED_EXTENSIONS = [
    "mp3","aac","m4a","ogg","oga","flac","wma","alac","amr","awb","opus",
    "ac3","eac3","aiff","aif","ape","mp4","mov","avi","mkv","wmv","flv",
    "webm","mpeg","mpg"
]

class ConvertError(Exception):
    pass


class Converter:
    @staticmethod
    def convert_wav(self, source: str, destination: str, talk: bool = False):
        if not source.lower().endswith(tuple(SUPPORTED_EXTENSIONS)):
            raise ConvertError("The source file does not seem to be a supported filetype for conversion.")

        if not destination.lower().endswith(".wav"):
            raise ConvertError("Destination file must have a .wav extension.")

        if not os.path.exists(source):
            raise ConvertError(f"Source file does not exist: {source}")

        cmd = [
            "ffmpeg",
            "-y",
            "-i", source,
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "48000",
            "-ac", "2",
            destination
        ]

        Log.converter(f"Converting {source} -> {destination}")

        if talk:
            Log.converter(f"ffmpeg command: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )

            if talk:
                if result.stdout:
                    Log.converter(f"ffmpeg stdout:\n{result.stdout}")
                if result.stderr:
                    Log.converter(f"ffmpeg stderr:\n{result.stderr}")

            Log.converter("Conversion completed successfully")

        except subprocess.CalledProcessError as e:
            Log.converter("ffmpeg conversion failed.")

            if talk:
                if e.stdout:
                    Log.converter(f"ffmpeg stdout:\n{e.stdout}")
                if e.stderr:
                    Log.converter(f"ffmpeg stderr:\n{e.stderr}")

            raise ConvertError("Failed to convert file to WAV.") from e
