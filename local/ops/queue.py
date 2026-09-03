from typing import Any

from shared.ops import CliOp

class QueueOp(CliOp):
    """
    The 'queue' command OP. Just a Queue.parse() redirect.
    """
    
    name = "queue"
    syntax = "[+|-|*|!|?]"
    short_help = "Manage the broadcast queue"
    long_help = """\
Manage the broadcast queue.
Use 'queue ?' for detailed help on the available operators.
"""
    examples = [
        "queue ?",
        "queue +myfile.wav,myfile2.wav"
    ]
    env_vars = {}

    async def handle(self, is_cmd: bool = False, cmd_parts: list[str] = []):
        self.owner.queue.parse(' '.join(cmd_parts))

def setup(reg: Any):
    reg.register(QueueOp)