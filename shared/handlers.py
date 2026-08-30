import os
from pathlib import Path
from typing import Awaitable, Callable

from shared.env import Env
from shared.logger import Log

class HandlerExecutor:
    
    def __init__(self, command_executor: Callable[..., Awaitable[bool]]):
        self.command_executor = command_executor

    @property
    def handlers_dir(self) -> str:
        return Env.get("HANDLERS_DIR", "/opt/BotWave/handlers/")
    
    async def execute_handler(self, file_path: str, ctx: dict[str, str] = {}, silent: bool = False):
        old_env = {k: os.environ.get(k) for k in ctx}

        try:
            os.environ.update(ctx)

            if not silent:
                Log.handler(f"Running handler on {file_path}")

            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()

                    if line and line[0] != "#":
                        if not silent:
                            Log.handler(f"Executing command: {line}")

                        await self.command_executor(line)

        except Exception as e:
            Log.error(f"Error executing command from {file_path}: {e}")

        finally:
            for k, v in old_env.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
    
    async def run_handlers(self, prefix: str, dir_path: str | None = None, context: dict[str, str] = {}):
        if dir_path is None:
            dir_path = self.handlers_dir
        
        if not Path(dir_path).is_dir():
            Log.error(f"Directory {dir_path} not found")
            return False
        
        for filename in os.listdir(dir_path):
            if filename.startswith(prefix):
                file_path = os.path.join(dir_path, filename)
                silent = filename.endswith(".shdl")
                
                if filename.endswith(".hdl") or silent:
                    await self.execute_handler(file_path, ctx=context, silent=silent)
    
    def list_handlers(self, dir_path: str | None = None):
        if dir_path is None:
            dir_path = self.handlers_dir
        
        if not Path(dir_path).is_dir():
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
    
    def list_handler_commands(self, filename: str, dir_path: str | None = None):
        if dir_path is None:
            dir_path = self.handlers_dir
        
        file_path = os.path.join(dir_path, filename)
        
        if not Path(file_path).is_file():
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