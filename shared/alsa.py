import time

try:
    import alsaaudio
    ALSA_AVAILABLE = True
except ImportError:
    ALSA_AVAILABLE = False

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
        if not ALSA_AVAILABLE:
            return False
        
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
        if not ALSA_AVAILABLE:
            return False

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