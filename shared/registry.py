import importlib.util
from pathlib import Path
import traceback

from shared.env import Env
from shared.logger import Log

# exception explicitly raised to pass a message to the dispatcher
class UpperException(Exception):
    pass

class Registry:
    def __init__(self, owner):
        self.owner = owner  # the main BotWave class
        self.operations = {}
        self.instances = []

    def register(self, op_cls):
        op = op_cls(self.owner, self)

        for key, method_name in op.commands.items():
            self.operations[key] = getattr(op, method_name)
            Log.debug(f"registered {key} in {op}")

        self.instances.append(op)

        return op  

    def from_dir(self, dir):
        path = Path(dir)

        if not path.is_dir():
            Log.error(f"{path} is not a directory")
            return

        for path in Path(dir).glob("*.py"):
            Log.debug(f"Processing op {path.name}")

            spec = importlib.util.spec_from_file_location(path.stem, path)
            op = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(op)

            if hasattr(op, "setup"):
                op.setup(self)

            else:
                Log.error(f"Op '{path.name}' has no setup() function")


    async def dispatch(self, key: str, *args, **kwargs):
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

    def get_instances(self):
        return self.instances