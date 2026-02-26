import errno
import os
import tempfile

from shared.logger import Log
class TipEngine:
    def __init__(self, is_server: bool = True):
        self.__lockfile = os.path.join(tempfile.gettempdir(), f"botwave_{'server' if is_server else 'client'}.pid")

    def __pid_exists(self, pid: int) -> bool:
        if pid <= 0:
            return False

        try:
            os.kill(pid, 0)
        except OSError as e:
            # ESRCH = No such process
            if e.errno == errno.ESRCH:
                return False
            
            # EPERM = Process exists but no permission
            elif e.errno == errno.EPERM:
                return True
            
            else:
                return False
        else:
            return True    

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

        if self.__pid_exists(pid):
            Log.warning(f"Another BotWave instance may already be running (PID {pid}). This could cause conflicts.")

        else:
            os.remove(self.__lockfile)

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