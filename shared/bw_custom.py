# piwave/backend/bw_custom.py

from piwave.backends.base import Backend, BackendError
from pathlib import Path

class BWCustom(Backend):
    @property
    def name(self):
        return "bw_custom"

    @property
    def frequency_range(self):
        return (76.0, 108.0)

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
        return "bw_custom"

    def _get_search_paths(self):
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