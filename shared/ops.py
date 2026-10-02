import shlex
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
    short_help: str = ""
    long_help: str = ""
    examples: list[str] = []
    env_vars: dict[str, tuple[str, str]] = {}

    def __init__(self, owner: Any, registry: "Registry"):
        self.owner = owner
        self.registry = registry

    @property
    def commands(self) -> dict[str, str]:
        return {self.name: "handle"}

class AliasOp(CliOp):
    original_name: str = ""
    command: str = ""

    async def handle(self, is_cmd: bool = False, cmd_parts: list[str] = []):
        parts = shlex.split(self.command) + cmd_parts
        await self.registry.dispatch(parts[0].lower(), is_cmd=True, cmd_parts=parts[1:])