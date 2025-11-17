import os
from typing import Callable
from shared.logger import Log

class HandlerExecutor:
    
    def __init__(self, handlers_dir: str, command_executor: Callable):
        self.handlers_dir = handlers_dir
        self.command_executor = command_executor
    
    def execute_handler(self, file_path: str, silent: bool = False):
        try:
            if not silent:
                Log.handler(f"Running handler on {file_path}")
            
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and line[0] != "#":
                        if not silent:
                            Log.handler(f"Executing command: {line}")
                        self.command_executor(line)
        except Exception as e:
            Log.error(f"Error executing command from {file_path}: {e}")
    
    def run_handlers(self, prefix: str, dir_path: str = None):
        if dir_path is None:
            dir_path = self.handlers_dir
        
        if not os.path.exists(dir_path):
            Log.error(f"Directory {dir_path} not found")
            return False
        
        for filename in os.listdir(dir_path):
            if filename.startswith(prefix):
                file_path = os.path.join(dir_path, filename)
                silent = filename.endswith(".shdl")
                if filename.endswith(".hdl") or silent:
                    self.execute_handler(file_path, silent=silent)
    
    def list_handlers(self, dir_path: str = None):
        if dir_path is None:
            dir_path = self.handlers_dir
        
        if not os.path.exists(dir_path):
            Log.error(f"Directory {dir_path} not found")
            return False
        
        try:
            handlers = [f for f in os.listdir(dir_path) 
                       if os.path.isfile(os.path.join(dir_path, f))]
            
            if not handlers:
                Log.info(f"No handlers found in {dir_path}")
                return
            
            Log.info(f"Handlers in directory {dir_path}:")
            for handler in handlers:
                Log.print(f"  {handler}", 'white')
        except Exception as e:
            Log.error(f"Error listing handlers: {e}")
    
    def list_handler_commands(self, filename: str, dir_path: str = None):
        if dir_path is None:
            dir_path = self.handlers_dir
        
        file_path = os.path.join(dir_path, filename)
        
        if not os.path.exists(file_path):
            Log.error(f"Handler file {filename} not found")
            return False
        
        try:
            Log.info(f"Commands in handler file {filename}:")
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        Log.print(f"  {line}", 'white')
        except Exception as e:
            Log.error(f"Error listing commands from {filename}: {e}")