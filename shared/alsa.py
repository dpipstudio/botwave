import alsaaudio
import time

from .logger import Log

class Alsa:
    def __init__(self, device_name="hw:BotWave,1", rate=48000, channels=2, period_size=1024):
        self.device_name = device_name
        self.rate = rate
        self.channels = channels
        self.period_size = period_size
        self.capture = None
        self._running = False

    def is_supported(self):
        """
        Checks if the BotWave ALSA loopback device is available
        """
        try:
            cards = alsaaudio.cards()
            # Check for "BotWave" in the list of soundcard names
            # Or check if we can successfully initialize the PCM device
            if any("BotWave" in card for card in cards):
                return True
            return False
        except Exception:
            return False

    def start(self):
        """
        Initializes the ALSA capture interface
        """
        try:
            self.capture = alsaaudio.PCM(
                type=alsaaudio.PCM_CAPTURE,
                mode=alsaaudio.PCM_NORMAL,
                device=self.device_name,
                channels=self.channels,
                rate=self.rate,
                format=alsaaudio.PCM_FORMAT_S16_LE,
                periodsize=self.period_size
            )
            self._running = True
            return True
        except alsaaudio.ALSAAudioError:
            Log.alsa(f"ALSA Error: Could not open {self.device_name}.")
            Log.alsa("Has the loopback device been set up correctly ?")
            return False

    def audio_generator(self):
        """
        Generator that yields raw PCM data.
        It blocks when no audio is playing from the source
        """
        if not self.capture:
            Log.alsa("Error: Capture not started.")
            return

        while self._running:
            try:
                # read() blocks until period_size samples are available
                length, data = self.capture.read()
                if length > 0:
                    yield data
            except alsaaudio.ALSAAudioError:
                # Xruns
                if self.capture:
                    self.capture.prepare()
                continue
            except Exception:
                break

    def stop(self):
        """
        Stops the generator loop and releases the ALSA device.
        """
        self._running = False
        if self.capture:
            time.sleep(0.1) # wait gen loop
            self.capture.close()
            self.capture = None