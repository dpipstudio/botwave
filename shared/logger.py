from dlogger import DLogger
import asyncio

class Logger(DLogger):
    ICONS = {
        'success': 'OK',
        'error': 'ERR',
        'warning': 'WARN',
        'info': 'INFO',
        'client': 'CLIENT',
        'server': 'SERVER',
        'broadcast': 'BCAST',
        'file': 'FILE',
        'handler': 'HNDL',
        'version': 'VER',
        'update': 'UPD',
        'sstv': 'SSTV',
        'auth': 'AUTH',
        'tls': 'TLS',
        'morse': 'MORSE'
    }

    STYLES = {
        'success': 'bright_green',
        'error': 'bright_red',
        'warning': 'bright_yellow',
        'info': 'bright_cyan',
        'client': 'magenta',
        'server': 'cyan',
        'broadcast': 'bright_magenta',
        'file': 'yellow',
        'handler': 'magenta',
        'version': 'bright_cyan',
        'update': 'bright_yellow',
        'sstv': 'bright_blue',
        'auth': 'blue',
        'tls': 'red',
        'morse': 'purple'
    }

    ws_clients = set()
    ws_loop = None

    def __init__(self):
        # Initialize with prebuilt icons & styles and ws support.
        
        super().__init__(
            icons=self.ICONS,
            styles=self.STYLES
        )

    def print(self, message: str, style: str = '', icon: str = '', end: str = '\n') -> None:
        super().print(message=message, style=style, icon=icon, end=end)

        ws_message = f"[{icon}] {message}" if icon else message

        for ws in list(self.ws_clients):
            try:
                if self.ws_loop:
                    asyncio.run_coroutine_threadsafe(ws.send(ws_message), self.ws_loop)
            except Exception as e:
                self.warn(f"Error sending to WebSocket client: {e}")
                try:
                    self.ws_clients.discard(ws)
                except Exception:
                    pass


Log = Logger()