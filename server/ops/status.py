from shared.env import Env
from shared.logger import Log
from shared.ops import CliOp
from shared.protocol import Commands

class StatusOp(CliOp):
    name = "status"
    syntax = "[targets]"

    async def handle(
            self,
            targets: list = [],
            is_cmd: bool = False,
            cmd_parts: list = []
    ):
        if is_cmd:
            targets = self.parse(cmd_parts)

            targets_resolved = False

            if targets:
                targets_resolved = self.owner.parse_targets(targets)


        if targets and not targets_resolved:
            Log.warning("No client(s) found matching the query")

        else:
            results = {'success': [], 'failed': []}

            for client_id in targets_resolved:
                if client_id not in self.owner.clients:
                    Log.error(f"  {client_id}: Client not found")
                    results['failed'].append(client_id)
                    continue

                client = self.owner.clients[client_id]

                try:
                    response = await client.proto.send(Commands.STATUS)
                    kwargs = response['kwargs']
                    status = kwargs.get('status', 'unknown')

                    Log.print(f"{client.get_display_name()}:", "bright_yellow")

                    if status == 'onair':
                        Log.print(f"  On Air", "bright_green")
                        Log.print(f"  File      : {kwargs.get('file', '?')}", "white")
                        Log.print(f"  Frequency : {kwargs.get('frequency', '?')} MHz", "white")
                        Log.print(f"  Uptime    : {kwargs.get('uptime', '?')}", "white")
                    else:
                        Log.print(f"  Idle", "orange")

                    results['success'].append(client_id)

                except TimeoutError:
                    Log.error(f"  {client.get_display_name()}: Response timeout")
                    results['failed'].append(client_id)

                except RuntimeError as e:
                    Log.error(f"  {client.get_display_name()}: {e}")
                    results['failed'].append(client_id)

                Log.print("")

            Log.info(f"Success: {len(results['success'])}, Failure: {len(results['failed'])}")
            Log.print("")

        Log.print(f"Connected clients : {len(self.owner.clients)}", "white")
        Log.print(f"Port              : {Env.get("PORT")}", "white")
        Log.print(f"File Port         : {Env.get('FPORT')}", "white")

        rmt = Env.get("REMOTE_CMD_PORT")
        if rmt:
            Log.print(f"RC Port           : {rmt}", "white")
            Log.print(f"RC Clients        : {self.owner.rc_clients}", "white")

        Log.print(f"Passkey           : {'yes' if Env.get("PASSKEY") else 'no'}", "white")


    def parse(self, cmd_parts):
        targets = cmd_parts[0] if len(cmd_parts) > 0 else None

        return targets

def setup(reg):
    reg.register(StatusOp)