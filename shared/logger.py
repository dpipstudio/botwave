from dlogger import DLogger
import asyncio
import re
import sys

from shared.env import Env

try:
    import readline
    HAS_READLINE = True
except ImportError:
    HAS_READLINE = False

INPUT_ACTIVE = False

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
        'morse': 'MORSE',
        'alsa': 'ALSA',
        'queue': 'QUEUE',
        'converter': 'CVRT',
        'environ': 'ENV'
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
        'morse': 'purple',
        'alsa': 'pink',
        'queue': 'orange',
        'converter': 'rgb(50,215,165)',
        'environ': 'rgb(224,107,61)'
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
        has_tty = HAS_READLINE and sys.stdin.isatty()
        #print(INPUT_ACTIVE)

        if has_tty:
            current_line = readline.get_line_buffer()

            if INPUT_ACTIVE:
                sys.stdout.write('\r' + ' ' * (len(current_line) + 20) + '\r')
                sys.stdout.flush()


        if Env.get_bool("REDACT_IPV4"):
            message = self.__redact_ipv4(message)

        super().print(message=message, style=style, icon=icon, end=end)

        if has_tty and INPUT_ACTIVE:
            prompt = f'\033[1;32m{Env.get("PROMPT_TEXT", "botwave › ")}\033[0m'
            sys.stdout.write(prompt + current_line)
            sys.stdout.flush()

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

    def __redact_ipv4(text: str) -> str:
        return re.sub(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', '[REDACTED]', text)

def toggle_input(is_active=None):
    global INPUT_ACTIVE

    if is_active is None:
        INPUT_ACTIVE = not INPUT_ACTIVE
    else:
        INPUT_ACTIVE = bool(is_active)

        

Log = Logger()