from typing import Any

from shared.logger import Log
from shared.ops import GeneralOp
from shared.protocol import Commands
from shared.protomanager import ParsedCommand
from shared.registry import UpperException

class KickOp(GeneralOp):
    """
    The OP handling Commands.KICK. Basically raises
    an UpperException() so the client stops.
    """

    commands = {Commands.KICK: "kick"}

    async def kick(self, parsed: ParsedCommand):
        kwargs = parsed['kwargs']

        reason = kwargs.get('reason', 'Kicked by administrator')
        Log.warning(f"Kicked: {reason}")
        raise UpperException("kick")

def setup(reg: Any):
    reg.register(KickOp)