import errno
import os
import psutil
import tempfile
import threading
import time

from shared.env import Env
from shared.logger import Log

class TipEngine:
    def __init__(self, is_server: bool = True):
        self.is_broadcasting = False
        
        self.__lockfile = os.path.join(tempfile.gettempdir(), f"botwave_{'server' if is_server else 'client'}.pid")
        self.__monitor_thread = None
        self.__monitor_stop = threading.Event()

    def __monitor_resources(self):
        poll_interval = Env.get_int("RESOURCE_POLL_INTERVAL", 10) # seconds between each cpu/ram check
        warn_cooldown = Env.get_int("RESOURCE_WARN_COOLDOWN", 60) # seconds between repeated warnings
        cpu_threshold = Env.get_int("RESOURCE_CPU_THRESHOLD", 80) # % cpu
        ram_threshold = Env.get_int("RESOURCE_RAM_THRESHOLD", 90) # % ram

        last_warned_at = 0

        while not self.__monitor_stop.is_set():
            self.__monitor_stop.wait(poll_interval)

            if self.__monitor_stop.is_set():
                break

            try:
                cpu = psutil.cpu_percent(interval=None)  # non-blocking
                ram = psutil.virtual_memory().percent

                now = time.monotonic()
                issues = []

                if cpu >= cpu_threshold:
                    issues.append(f"CPU at {cpu:.0f}% (threshold: {cpu_threshold}%)")

                if ram >= ram_threshold:
                    issues.append(f"RAM at {ram:.0f}% (threshold: {ram_threshold}%)")

                if issues and self.is_broadcasting and (now - last_warned_at) >= warn_cooldown:
                    for issue in issues:
                        Log.warning(f"High resource usage detected: {issue}. Backend may struggle.")
                    last_warned_at = now

            except Exception:
                pass  # don't let a psutil hiccup kill the monitor

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
        try:
            with open(self.__lockfile, "w") as f:
                f.write(str(os.getpid()))
                
        except OSError:
            pass

    def start(self):
        self.__check_lock_conflict()
        self.__write_lockfile()

        psutil.cpu_percent(interval=None) # kick psutil interval sampler
        self.__monitor_thread = threading.Thread(target=self.__monitor_resources, daemon=True)
        self.__monitor_thread.start()

    def stop(self):
        self.__monitor_stop.set()


        if os.path.exists(self.__lockfile):
            try:
                os.remove(self.__lockfile)

            except OSError:
                pass