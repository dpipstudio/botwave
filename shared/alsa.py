import time

try:
    import alsaaudio
    ALSA_AVAILABLE = True
except ImportError:
    ALSA_AVAILABLE = False

from shared.logger import Log
from shared.env import Env

class Alsa:
    def __init__(self):
        self.capture = None
        self._running = False

    @property
    def device_name(self):
        return f"hw:{Env.get('ALSA_CARD', 'BotWave')},1"

    @property
    def rate(self):
        return Env.get_int("ALSA_RATE", 48000)

    @property
    def channels(self):
        return Env.get_int("ALSA_CHANNELS", 2)

    @property
    def period_size(self):
        return Env.get_int("ALSA_PERIODSIZE", 1024)

    def is_supported(self):
        """
        Checks if the BotWave ALSA loopback device is available
        """
        if not ALSA_AVAILABLE:
            return False
        
        try:
            cards = alsaaudio.cards()
            # Check for "BotWave" in the list of soundcard names
            # Or check if we can successfully initialize the PCM device
            if any(Env.get("ALSA_CARD", "BotWave") in card for card in cards):
                return True
            
            return False
        
        except Exception:
            return False

    def start(self):
        """
        Initializes the ALSA capture interface
        """
        if not ALSA_AVAILABLE:
            return False

        try:
            if self._running:
                self.stop()

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
        if not ALSA_AVAILABLE:
            return False

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
                continue
            except Exception:
                break

    def stop(self):
        """
        Stops the generator loop and releases the ALSA device.
        """

        if not ALSA_AVAILABLE:
            return False
        
        self._running = False
        if self.capture:
            time.sleep(0.1) # wait gen loop
            self.capture.close()
            self.capture = None