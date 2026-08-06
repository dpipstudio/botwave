from datetime import datetime, timezone

from shared.env import Env
from shared.logger import Log
from shared.ops import CliOp
from shared.protocol import Commands

class StartOp(CliOp):
    """
    The 'start' command OP. Starts a broadcast on the target client.

    If WAIT_START is set to true, it schedules a broadcast based on
    now() + 5s per (clients - 1). This was intended to let clients
    sync their broadcasts, but isn't really working.
    """

    name = "start"
    syntax = "<targets> <file> [frequency] [loop] [ps] [rt] [pi]"

    async def handle(
        self,
        targets: list = [],
        file: str = None,
        freq: float = 90,
        loop: bool = False,
        ps: str = "BotWave",
        rt: str = "Broadcasting",
        pi: str = "FFFF",
        is_cmd: bool = False,
        cmd_parts: list = []
    ):
        if is_cmd:
            targets, file, freq, loop, ps, rt, pi = self.parse(cmd_parts)

            if not targets:
                return

            targets = self.owner.parse_targets(targets)

            if not targets:
                Log.warning("No client(s) found matching the query")
                return

            self.owner.queue.manual_pause()

        # calculate start_at timestamp if wait_start is enabled
        # start_at = now() + 5s per (clients - 1) 
        if Env.get_bool("WAIT_START") and len(targets) > 1:
            start_at = datetime.now(timezone.utc).timestamp() + 5 * (len(targets) - 1)
            Log.broadcast(f"Starting broadcast at {datetime.fromtimestamp(start_at)}")

        else:
            start_at = 0
            Log.broadcast(f"Starting broadcast ASAP")

        Log.broadcast(f"Starting broadcast on {len(targets)} client(s)...")

        results = {'started': [], 'failed': []}
        
        for client_id in targets:
            if client_id not in self.owner.clients:
                Log.error(f"  {client_id}: Client not found")
                results['failed'].append(client_id)
                continue

            
            client = self.owner.clients[client_id]
            
            try: 
                response = await client.proto.send(
                    Commands.START,
                    filename=file,
                    freq=freq,
                    ps=ps,
                    rt=rt,
                    pi=pi,
                    loop='true' if loop else 'false',
                    start_at=start_at
                )

                Log.success(f"  {client.get_display_name()}: {response['kwargs'].get('message', 'Broadcast started')}")
                results['started'].append(client_id)

            except TimeoutError:
                Log.error(f"  {client.get_display_name()}: Response timeout")
                results['failed'].append(client_id)

            except RuntimeError as e:
                err = str(e)

                Log.error(f"  {client.get_display_name()}: {err}")
                results['failed'].append((client_id, err))

        Log.print("")        
        Log.info(f"Success: {len(results['started'])}, Failure: {len(results['failed'])}")

        await self.registry.dispatch("handlers_onstart",  context={"BW_BROADCAST_FILE": file, "BW_BROADCAST_FREQ": str(freq)})

    def parse(self, cmd_parts):
        if len(cmd_parts) < 2:
            Log.error("Usage: start <targets> <file> [frequency] [loop] [ps] [rt] [pi]")
            return (None, None, None, None, None, None, None)

        targets = cmd_parts[0]
        file = cmd_parts[1]
        frequency = float(cmd_parts[2]) if len(cmd_parts) > 2 else Env.get_float("DEFAULT_FREQ", 90)
        loop = cmd_parts[3].lower() == 'true' if len(cmd_parts) > 3 else False
        ps = cmd_parts[4] if len(cmd_parts) > 4 else Env.get("DEFAULT_PS", "BotWave")
        rt = cmd_parts[5] if len(cmd_parts) > 5 else Env.get("DEFAULT_RT",  cmd_parts[1]) # file name
        pi = cmd_parts[6] if len(cmd_parts) > 6 else Env.get("DEFAULT_PI", "FFFF")

        return (targets, file, frequency, loop, ps, rt, pi)

def setup(reg):
    reg.register(StartOp)