from shared.logger import Log

class Registry:
    def __init__(self, owner):
        self.owner = owner  # the main BotWave class
        self.operations = {}

    def register(self, op_cls):
        op = op_cls(self.owner)

        for key, method_name in op.commands.items():
            self.operations[key] = getattr(op, method_name)

        return op  

    async def dispatch(self, key: str, *args, **kwargs):
        op = self.operations.get(key)

        if not op:
            return False

        try:
            await op(*args, **kwargs)

        except Exception as e:  # Shouldn't happen, try/catch in ops
            Log.error(f"Unexpected error in '{key}': {e}")

        return True

    def get(self, name: str):
        return self.operations.get(name)

    def get_all(self):
        return self.operations