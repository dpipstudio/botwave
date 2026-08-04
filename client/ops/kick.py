from shared.logger import Log
from shared.ops import GeneralOp
from shared.protocol import Commands
from shared.registry import UpperException

class KickOp(GeneralOp):
    commands = {Commands.KICK: "kick"}

    async def kick(self, parsed):
        kwargs = parsed['kwargs']

        reason = kwargs.get('reason', 'Kicked by administrator')
        Log.warning(f"Kicked: {reason}")
        raise UpperException("kick")

def setup(reg):
    reg.register(KickOp)