class GeneralOp:
    commands: dict = {}

    def __init__(self, owner, registry):
        self.owner = owner
        self.registry = registry

class CliOp:
    name: str = None
    syntax: str = ""

    def __init__(self, owner, registry):
        self.owner = owner
        self.registry = registry

    @property
    def commands(self) -> dict:
        return {self.name: "handle"}