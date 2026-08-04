from dlogger import DLogger
import asyncio
import contextvars
import re

from shared.env import Env

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
        'update': 'bright_yellow bold',
        'sstv': 'bright_blue',
        'auth': 'blue',
        'tls': 'red',
        'morse': 'purple',
        'alsa': 'pink',
        'queue': 'orange',
        'debug': 'orange',
        'converter': 'rgb(50,215,165)',
        'environ': 'rgb(224,107,61)'
    }

    ws_clients = set()
    ws_loop = None

    def __init__(self):
        # Initialize with prebuilt icons & styles and ws support.
        
        show_time = Env.get_bool("LOG_TIME")
        time_format = Env.get("LOG_TIME_FORMAT", "%Y-%m-%d %H:%M:%S")
        save_to = Env.get("LOG_FILE")
        save = True if save_to else False

        self.transaction_id = contextvars.ContextVar('transaction_id', default=None)
        self.remote_cmd_socket = contextvars.ContextVar('remote_cmd_socket', default=None)
        
        super().__init__(
            icons=self.ICONS,
            styles=self.STYLES,
            show_time=show_time,
            time_format=time_format,
            save=save,
            save_to=save_to,
            single_file=True
        )

    def print(self, message: str, style: str = '', icon: str = '', end: str = '\n') -> None:
        if icon == "debug" and not Env.get_bool("TALK"):
            return

        tx_id = self.transaction_id.get()
        if tx_id:
            message = f"{message}transaction_id={tx_id}"

        if Env.get_bool("REDACT_IPV4"):
            message = self.__redact_ipv4(message)

        super().print(message=message, style=style, icon=icon, end=end)

        ws_message = f"[{icon}] {message}" if icon else message
        origin_ws = self.remote_cmd_socket.get()

        if Env.get_bool("ISOLATE_REMOTE", True) and origin_ws:
            try:
                if self.ws_loop:
                    asyncio.run_coroutine_threadsafe(origin_ws.send(ws_message), self.ws_loop)
            except Exception as e:
                self.warn(f"Error sending to WebSocket client: {e}")
        else:
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

    def end(self):
        # sends "ENDtransaction_id=<tid>" if a transaction_id is set
        if self.transaction_id.get():
            self.print("END") # transaction_id will automatically be appended

    def __redact_ipv4(self, text: str) -> str:
        return re.sub(r'(?:\d{1,3}\.){3}\d{1,3}', '[REDACTED]', text)
    
    def set_transaction_id(self, tx_id: str):
        self.transaction_id.set(tx_id)

    def clear_transaction_id(self):
        self.transaction_id.set(None)

    def set_remote_cmd(self, socket):
        self.remote_cmd_socket.set(socket)

    def clear_remote_cmd(self):
        self.remote_cmd_socket.set(None)


Log = Logger()