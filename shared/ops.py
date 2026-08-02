class GeneralOp:
    commands: dict = {}

    def __init__(self, owner):
        self.owner = owner

class CliOp:
    name: str = None
    syntax: str = ""

    def __init__(self, owner):
        self.owner = owner

    @property
    def commands(self) -> dict:
        return {self.name: "handle"}