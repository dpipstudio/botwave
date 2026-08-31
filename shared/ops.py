from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from shared.registry import Registry

class GeneralOp:
    commands: dict[str, str] = {}

    def __init__(self, owner: Any, registry: "Registry"):
        self.owner = owner
        self.registry = registry

class CliOp:
    name: str = ""
    syntax: str = ""

    def __init__(self, owner: Any, registry: "Registry"):
        self.owner = owner
        self.registry = registry

    @property
    def commands(self) -> dict[str, str]:
        return {self.name: "handle"}