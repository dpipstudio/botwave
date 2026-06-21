import threading
import queue
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
        self._subscribers = []
        self._sub_lock = threading.Lock()
        self._reader_thread = None

    @property
    def device_name(self):
        return f"{Env.get('ALSA_INTERFACE', 'hw')}:{Env.get('ALSA_CARD', 'BotWave')},{Env.get('ALSA_DEVICE', '1')}"

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
        Initializes the ALSA capture interface and starts the single reader thread
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
            self._reader_thread = threading.Thread(target=self._read_loop, daemon=True)
            self._reader_thread.start()
            return True
        
        except alsaaudio.ALSAAudioError:
            Log.alsa(f"ALSA Error: Could not open {self.device_name}.")
            Log.alsa("Has the loopback device been set up correctly ?")
            return False

    def _read_loop(self):
        """
        Single thread that does all the capture.read() calls and fans the
        data out to every subscriber. Stops clients from fighting over reads.
        """
        while self._running:
            try:
                # read() blocks until period_size samples are available
                length, data = self.capture.read()
                if length > 0:
                    with self._sub_lock:
                        for q in self._subscribers:
                            try:
                                q.put_nowait(data)
                            except queue.Full:
                                # client too slow, drop oldest instead of stalling the rest
                                try:
                                    q.get_nowait()
                                except queue.Empty:
                                    pass
                                try:
                                    q.put_nowait(data)
                                except queue.Full:
                                    pass
            except alsaaudio.ALSAAudioError:
                # Xruns
                continue
            except Exception:
                break

    def subscribe(self):
        """
        Registers a new client, returns the queue it'll receive audio on
        """
        q = queue.Queue(maxsize=50)
        with self._sub_lock:
            self._subscribers.append(q)
        return q

    def unsubscribe(self, q):
        with self._sub_lock:
            if q in self._subscribers:
                self._subscribers.remove(q)

    def audio_generator(self, q):
        """
        Generator that yields raw PCM data for one subscriber.
        It blocks when no audio is available yet.
        """
        if not ALSA_AVAILABLE:
            return False

        while self._running:
            try:
                yield q.get(timeout=1)
            except queue.Empty:
                continue

    def stop(self):
        """
        Stops the reader thread, drops all subscribers, and releases the ALSA device.
        """

        if not ALSA_AVAILABLE:
            return False
        
        self._running = False

        if self._reader_thread:
            self._reader_thread.join(timeout=1)
            self._reader_thread = None

        with self._sub_lock:
            self._subscribers.clear()

        if self.capture:
            time.sleep(0.1) # wait gen loop
            self.capture.close()
            self.capture = None