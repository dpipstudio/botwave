import os
from contextvars import ContextVar
from pathlib import Path
from typing import Any, Awaitable, Callable

from shared.env import Env
from shared.logger import Log
from shared.ops import GeneralOp
from shared.registry import Registry

class HandlerRun:
    """
    Tracks a running handler, so ops that dispatch commands
    on their own (like '|') can tell it to stop.
    """
    stopped: bool = False
    finished: bool = False

class HandlerExecutor:

    current_run: ContextVar[HandlerRun | None] = ContextVar("current_run", default=None)
    
    def __init__(self, command_executor: Callable[..., Awaitable[None]]):
        self.command_executor = command_executor

    @property
    def handlers_dir(self) -> str:
        return Env.get("HANDLERS_DIR", "/opt/BotWave/handlers/")

    @property
    def stopped(self) -> bool:
        """
        True if the handler running in this context already ran 'exit'.
        """
        run = self.current_run.get()
        return bool(run and run.stopped and not run.finished)

    def register(self, registry: Registry):
        handlers_dir = Path(self.handlers_dir)
        if not handlers_dir.is_dir():
            Log.warning(f"{handlers_dir} does not exist, skipping handlers registration")
            return

        for handler in [f for f in handlers_dir.iterdir() if f.suffix in (".hdl", ".shdl")]:
            try:
                with open(handler, "r", encoding="utf-8") as f:
                    content = f.readlines()

                async def handle(self: Any, handler: Path = handler, content: list[str] = content, context: dict[str, str] = {}):
                    await self.owner.handlers_executor.execute_handler(
                        str(handler),
                        context,
                        True if handler.suffix == ".shdl" else False,
                        lines=content
                    )

                op = type(f"HDL_{handler.stem}", (GeneralOp,), {
                    "commands": {handler.stem: "handle"},
                    "handle": handle
                })

                registry.register(op)

            except Exception as e:
                Log.warning(f"Failed to load '{handler}': {e}")


    async def execute_handler(self, file_path: str, ctx: dict[str, str] = {}, silent: bool = False, lines: list[str] = []):
        old_env = {k: os.environ.get(k) for k in ctx}
        run = HandlerRun()
        token = self.current_run.set(run)

        try:
            os.environ.update(ctx)

            if not silent:
                Log.handler(f"Running handler on {file_path}")

            if lines:
                for line in lines:
                    await self.exec_line(line, silent)

            else:
                with open(file_path, "r", encoding="utf-8") as f:
                    for line in f:
                        await self.exec_line(line, silent)

        except Exception as e:
            Log.error(f"Error executing command from {file_path}: {e}")

        finally:
            run.finished = True
            self.current_run.reset(token)

            for k, v in old_env.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    async def exec_line(self, line: str, silent: bool = False):
        """
        Executes a line with the command_executor.
        """

        line = line.strip()

        if line and line[0] != "#":
            if not silent:
                Log.handler(f"Executing command: {line}")

            await self.command_executor(line)

    def stop_handler(self) -> bool:
        """
        To be called by the 'exit' ops. If a handler is currently running, flags
        it as stopped and returns True (the op must NOT shut anything down).
        """
        run = self.current_run.get()

        if run and not run.finished:
            Log.debug("Handler ran 'exit', stopping execution")
            run.stopped = True
            return True

        return False
    
    def list_handlers(self, dir_path: str = ""):
        if not dir_path:
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
    
    def list_handler_commands(self, filename: str, dir_path: str = ""):
        if not dir_path:
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