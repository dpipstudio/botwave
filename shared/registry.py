import importlib.util
from pathlib import Path
import traceback

from shared.logger import Log

class Registry:
    def __init__(self, owner):
        self.owner = owner  # the main BotWave class
        self.operations = {}

    def register(self, op_cls):
        op = op_cls(self.owner, self)

        for key, method_name in op.commands.items():
            self.operations[key] = getattr(op, method_name)

        return op  

    def from_dir(self, dir):
        path = Path(dir)

        if not path.is_dir():
            Log.error(f"{path} is not a directory")
            return

        for path in Path(dir).glob("*.py"):

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
            return False

        try:
            await op(*args, **kwargs)

        except Exception as e:  # Shouldn't happen, try/catch in ops
            Log.error(f"Unexpected error in '{key}': {e}\n{traceback.format_exc()}")

        return True

    def get(self, name: str):
        return self.operations.get(name)

    def get_all(self):
        return self.operations