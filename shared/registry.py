import importlib.util
import traceback
from pathlib import Path
from typing import Any, Callable, TYPE_CHECKING

from shared.env import Env
from shared.logger import Log

if TYPE_CHECKING:
    from client.client import BotWaveClient
    from local.local import BotWaveLocal
    from server.server import BotWaveServer
    from shared.ops import CliOp, GeneralOp

# exception explicitly raised to pass a message to the dispatcher
class UpperException(Exception):
    pass

class Registry:
    def __init__(self, owner: "BotWaveClient | BotWaveLocal | BotWaveServer"):
        self.owner = owner  # the main BotWave class
        self.operations: dict[str, Callable[..., Any]] = {}
        self.instances: dict[str, "CliOp | GeneralOp"] = {}

    def register(self, op_cls: "type[CliOp] | type[GeneralOp]"):
        op = op_cls(self.owner, self) # pyright: ignore

        for key, method_name in op.commands.items():
            self.operations[key] = getattr(op, method_name)
            Log.debug(f"registered {key} in {op}")

        self.instances[type(op).__name__] = op

        return op  

    def from_dir(self, dir: Path):

        if not dir.is_dir():
            Log.error(f"{dir} is not a directory")
            return

        for path in dir.glob("*.py"):
            Log.debug(f"Processing op {path.name}")

            spec = importlib.util.spec_from_file_location(path.stem, path)
            if not (spec and spec.loader):
                continue

            op = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(op)

            if hasattr(op, "setup"):
                op.setup(self)

            else:
                Log.error(f"Op '{path.name}' has no setup() function")


    async def dispatch(self, key: str, *args: Any, **kwargs: Any):
        op = self.operations.get(key)

        if not op:
            Log.debug(f"No such op: {op}")
            return False

        try:
            await op(*args, **kwargs)

        except UpperException as ue:
            Log.debug(f"Got an UpperException ({ue}), raising...")
            raise

        except Exception as e:  # Shouldn't happen, try/catch in ops
            Log.error(f"Unexpected error in '{key}': {e}")

            if Env.get_bool("TALK"):
                traceback.print_exc()

        return True

    def get_instances(self) -> dict[str, "CliOp | GeneralOp"]:
        return self.instances