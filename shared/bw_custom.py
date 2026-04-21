# piwave/backend/bw_custom.py

from piwave.backends.base import Backend, BackendError
from pathlib import Path

from shared.env import Env
from shared.logger import Log

class BWCustom(Backend):
    @property
    def name(self):
        path = Env.get("BACKEND_PATH")

        if path:
            return Path(path).name
        
        return "bw_custom"

    @property
    def frequency_range(self):
        min_freq = Env.get_int("BACKEND_MIN_FREQ", 76)
        max_freq = Env.get_int("BACKEND_MAX_FREQ", 108)
        return (min_freq, max_freq)

    @property
    def supports_rds(self):
        return True

    @property
    def supports_live_streaming(self):
        return True

    @property
    def supports_loop(self):
        return True

    def _get_executable_name(self):
        path = Env.get("BACKEND_PATH")

        if path:
            return Path(path).name
        
        return "bw_custom"

    def _get_search_paths(self):
        path = Env.get("BACKEND_PATH")

        if path:
            return [str(Path(path).parent)]
        
        return ["/opt/BotWave/backends/bw_custom/src", "/opt", "/usr/local/bin", "/usr/bin", "/bin", "/home"]

    def build_command(self, wav_file: str, loop: bool):
        if not Path(wav_file).exists():
            raise BackendError(f"Audio file does not exist: {wav_file}")

        cmd = [
            self.required_executable,
            "-freq", str(self.frequency),
            "-audio", wav_file,
            "-pi", self.pi,
            "-ps", self.ps,
            "-rt", self.rt
        ]

        if loop:
            cmd.append("-loop")

        return cmd

    def build_live_command(self, sample_rate=48000, channels=2):
        cmd = [
            self.required_executable,
            "-freq", str(self.frequency),
            "-audio", "-",
            "-raw",
            "-rate", str(sample_rate),
            "-channels", str(channels),
            "-pi", self.pi,
            "-ps", self.ps,
            "-rt", self.rt
        ]
        return cmd