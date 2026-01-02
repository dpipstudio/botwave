import shlex
from typing import Dict, Tuple

PROTOCOL_VERSION = "2.0.1"


class Commands:
    
    # auth
    AUTH = 'AUTH'
    VER = 'VER'
    REGISTER = 'REGISTER'
    
    # ping pong
    PING = 'PING'
    PONG = 'PONG'
    
    # broadcast
    START = 'START'
    STOP = 'STOP'
    
    # files
    UPLOAD_TOKEN = 'UPLOAD_TOKEN'
    DOWNLOAD_TOKEN = 'DOWNLOAD_TOKEN'
    DOWNLOAD_URL = 'DOWNLOAD_URL'
    STREAM_TOKEN = 'STREAM_TOKEN'
    
    # client managment
    KICK = 'KICK'
    
    # file managment
    LIST_FILES = 'LIST_FILES'
    REMOVE_FILE = 'REMOVE_FILE'
    
    # responses
    OK = 'OK'
    ERROR = 'ERROR'
    REGISTER_OK = 'REGISTER_OK'
    AUTH_FAILED = 'AUTH_FAILED'
    VERSION_MISMATCH = 'VERSION_MISMATCH'

class ProtocolParser:
    # parse protocol commands
    # should be able to support: COMMAND arg1 arg2 'quoted arg' key=value key2='value with spaces'
    
    @staticmethod
    def parse_command(line: str) -> Dict:
        """
        Parse a command line into structured data.
        
        Args:
            line (str): Command line to parse
        
        Returns:
            dict: {
                'command': str,      # Command name (uppercase)
                'args': List[str],   # Positional arguments
                'kwargs': Dict[str, str]  # Key-value pairs
            }
        
        Example:
            >>> parse_command("START file.wav freq=90.0 ps='My Radio'")
            {
                'command': 'START',
                'args': ['file.wav'],
                'kwargs': {'freq': '90.0', 'ps': 'My Radio'}
            }
        """
        line = line.strip()
        if not line:
            return {'command': '', 'args': [], 'kwargs': {}}
        
        try:
            tokens = shlex.split(line)
        except ValueError as e:
            raise ValueError(f"Invalid command syntax: {e}")
        
        if not tokens:
            return {'command': '', 'args': [], 'kwargs': {}}
        
        command = tokens[0].upper()
        args = []
        kwargs = {}
        
        for token in tokens[1:]:
            if '=' in token:
                # key=value pair
                key, value = token.split('=', 1)
                kwargs[key] = value
            else:
                args.append(token)
        
        return {
            'command': command,
            'args': args,
            'kwargs': kwargs
        }
    
    @staticmethod
    def build_command(command: str, *args, **kwargs) -> str:
        """
        Build a command line from structured data.
        
        Args:
            command (str): Command name
            *args: Positional arguments
            **kwargs: Key-value pairs
        
        Returns:
            str: Formatted command line
        
        Example:
            >>> build_command('START', 'file.wav', freq=90.0, ps='My Radio')
            "START file.wav freq=90.0 ps='My Radio'"
        """
        parts = [command.upper()]
        
        for arg in args:
            arg_str = str(arg)
            if ' ' in arg_str or "'" in arg_str or '"' in arg_str:
                parts.append(shlex.quote(arg_str))
            else:
                parts.append(arg_str)
        
        for key, value in kwargs.items():
            value_str = str(value)
            if ' ' in value_str or "'" in value_str or '"' in value_str:
                parts.append(f"{key}={shlex.quote(value_str)}")
            else:
                parts.append(f"{key}={value_str}")
        
        return ' '.join(parts)
    
    @staticmethod
    def parse_response(line: str) -> Tuple[str, str]:
        """
        Parse a simple response line (OK, ERROR, etc).
        
        Args:
            line (str): Response line
        
        Returns:
            tuple: (status, message)
        
        Example:
            >>> parse_response("OK")
            ('OK', '')
            >>> parse_response("ERROR message='File not found'")
            ('ERROR', 'File not found')
        """
        parsed = ProtocolParser.parse_command(line)
        status = parsed['command']
        message = parsed['kwargs'].get('message', '')
        
        return status, message
    
    @staticmethod
    def build_response(status: str, message: str = '') -> str:
        """
        Build a response line.
        
        Args:
            status (str): Response status (OK, ERROR, etc)
            message (str): Optional message
        
        Returns:
            str: Formatted response line
        """
        if message:
            return ProtocolParser.build_command(status, message=message)
        return status.upper()