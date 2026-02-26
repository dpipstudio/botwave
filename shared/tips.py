# shared/tips.py

import os
import tempfile
from shared.logger import Log

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

LOCKFILE_PATH = os.path.join(tempfile.gettempdir(), "botwave.pid")


class TipEngine:

    def __check_lock_conflict(self):
        if not os.path.exists(LOCKFILE_PATH):
            return

        try:
            with open(LOCKFILE_PATH) as f:
                pid = int(f.read().strip())

        except (ValueError, OSError):
            return

        if pid == os.getpid():
            return

        if PSUTIL_AVAILABLE:
            if psutil.pid_exists(pid):
                Log.warning(f"Another BotWave instance may already be running (PID {pid}). This could cause conflicts.")

            else:
                os.remove(LOCKFILE_PATH)
        else:
            Log.warning(f"A BotWave lockfile exists (PID {pid}). If no other instance is running, this is stale.")

    def __write_lockfile(self):
        with open(LOCKFILE_PATH, "w") as f:
            f.write(str(os.getpid()))

    def start(self):
        self.__check_lock_conflict()
        self.__write_lockfile()

    def stop(self):
        if os.path.exists(LOCKFILE_PATH):
            try:
                os.remove(LOCKFILE_PATH)
                
            except OSError:
                pass


Tips = TipEngine()