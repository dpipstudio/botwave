from shared.ops import CliOp

class QueueOp(CliOp):
    name = "queue"
    syntax = "[+|-|*|!|?]"

    async def handle(self, is_cmd: bool = False, cmd_parts: list = []):
        self.owner.queue.parse(' '.join(cmd_parts))

def setup(reg):
    reg.register(QueueOp)