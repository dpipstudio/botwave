# piwave monitor: monitors whenever the playback starts or ends
import asyncio
import threading
import time
from typing import Callable, Optional

class PWM: #pwm hehehe
    def __init__(self, check_interval: float = 1):
        self.check_interval = check_interval
        self.monitor_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.piwave = None
        self.on_finished_callback: Optional[Callable] = None
        self.event_loop: Optional[asyncio.AbstractEventLoop] = None
        
    def start(self, piwave, on_finished: Callable, event_loop: Optional[asyncio.AbstractEventLoop] = None):
        self.stop()
        
        self.piwave = piwave
        self.on_finished_callback = on_finished
        self.event_loop = event_loop or self._try_get_event_loop()
        self.stop_event.clear()
        
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True
        )
        self.monitor_thread.start()
    
    def _try_get_event_loop(self) -> Optional[asyncio.AbstractEventLoop]:
        try:
            return asyncio.get_running_loop()
        except RuntimeError:
            return None
    
    def _monitor_loop(self):
        while not self.stop_event.is_set():
            try:
                if self.piwave is None:
                    break
                
                status = self.piwave.get_status()
                is_active = status.get("is_playing", False) or status.get("is_live_streaming", False)
                if not is_active:
                    if self.on_finished_callback:
                        if self.event_loop and asyncio.iscoroutinefunction(self.on_finished_callback):
                            asyncio.run_coroutine_threadsafe(
                                self.on_finished_callback(),
                                self.event_loop
                            )
                        else:
                            callback_thread = threading.Thread(
                                target=self.on_finished_callback,
                                daemon=True
                            )
                            callback_thread.start()
                    break
                    
            except:
                break
            
            time.sleep(self.check_interval)
    
    def stop(self):
        self.stop_event.set()
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2)
        
        self.piwave = None
        self.on_finished_callback = None
        self.event_loop = None
    
    def is_monitoring(self) -> bool:
        return (self.monitor_thread is not None and 
                self.monitor_thread.is_alive() and 
                not self.stop_event.is_set())