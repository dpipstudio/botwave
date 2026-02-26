# shared/tips.py

import os
import tempfile
from shared.logger import Log

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

class TipEngine:
    def __init__(self, is_server: bool = True):
        self.__lockfile = os.path.join(tempfile.gettempdir(), f"botwave_{'server' if is_server else 'client'}.pid")

    def __check_lock_conflict(self):
        if not os.path.exists(self.__lockfile):
            return

        try:
            with open(self.__lockfile) as f:
                pid = int(f.read().strip())

        except (ValueError, OSError):
            return

        if pid == os.getpid():
            return

        if PSUTIL_AVAILABLE:
            if psutil.pid_exists(pid):
                Log.warning(f"Another BotWave instance may already be running (PID {pid}). This could cause conflicts.")

            else:
                os.remove(self.__lockfile)
        else:
            Log.warning(f"A BotWave lockfile exists (PID {pid}). If no other instance is running, this is stale.")

    def __write_lockfile(self):
        with open(self.__lockfile, "w") as f:
            f.write(str(os.getpid()))

    def start(self):
        self.__check_lock_conflict()
        self.__write_lockfile()

    def stop(self):
        if os.path.exists(self.__lockfile):
            try:
                os.remove(self.__lockfile)

            except OSError:
                pass