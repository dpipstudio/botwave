from shared.env import Env
from shared.logger import Log
from shared.ops import CliOp
from shared.protocol import Commands

class LiveOp(CliOp):
    name = "live"
    syntax = "<targets> [frequency] [ps] [rt] [pi]"

    async def handle(
        self,
        targets: list = [],
        freq: float = 90,
        ps: str = "BotWave",
        rt: str = "Streaming",
        pi: str = "FFFF",
        is_cmd: bool = False,
        cmd_parts: list = []
    ):
        if is_cmd:
            targets, freq, ps, rt, pi = self.parse(cmd_parts)

            if not targets:
                return

            targets = self.owner.parse_targets(targets)

            if not targets:
                Log.warning("No client(s) found matching the query")
                return

            self.owner.queue.manual_pause()

        if not self.owner.alsa.is_supported():
            Log.alsa("Live broadcast is not supported on this installation.")
            Log.alsa("Did you setup the ALSA loopback card correctly ?")
            return
                
        if not self.owner.alsa.start():
            return

        Log.broadcast(f"Sending stream tokens to {len(targets)} client(s)...")
        
        results = {'streamed': [], 'failed': []}
        
        for client_id in targets:
            if client_id not in self.owner.clients:
                Log.error(f"  {client_id}: Client not found")
                results["failed"].append(client_id)
                continue
            
            client = self.owner.clients[client_id]
            
            client_queue = self.owner.alsa.subscribe()
            token = self.owner.http_server.create_stream_token(
                self.owner.alsa.audio_generator(client_queue),
                self.owner.alsa.rate,
                self.owner.alsa.channels
            )

            try:
                response = await client.proto.send(
                    Commands.STREAM_TOKEN,
                    token=token,
                    rate=self.owner.alsa.rate,
                    channels=self.owner.alsa.channels,
                    frequency=freq,
                    ps=ps,
                    rt=rt,
                    pi=pi
                )

                results["streamed"].append(client_id)
                Log.success(f"  {client.get_display_name()}: {response['kwargs'].get('message', 'Success')}")

            except TimeoutError:
                results["failed"].append(client_id)
                Log.error(f"  {client.get_display_name()}: Response timeout")

            except RuntimeError as e:
                results["failed"].append(client_id)
                Log.error(f"  {client.get_display_name()}: {str(e)}")

        Log.print("")    
        Log.info(f"Success: {len(results['streamed'])}, Failure: {len(results['failed'])}")
        
        card = Env.get("ALSA_CARD", 'BotWave')
        Log.alsa(f"To play live, please set your output sound card (ALSA) to '{card}'.")
        Log.alsa(f"We're expecting {self.owner.alsa.rate}kHz on {self.owner.alsa.channels} channels.")

        
    def parse(self, cmd_parts):
        if len(cmd_parts) < 1:
            Log.error("Usage: live <targets> [frequency] [ps] [rt] [pi]")
            return (None, None, None, None, None)

        targets = cmd_parts[0]
        frequency = float(cmd_parts[1]) if len(cmd_parts) > 1 else Env.get_float("DEFAULT_FREQ", 90)
        ps = cmd_parts[2] if len(cmd_parts) > 2 else Env.get("DEFAULT_PS", "BotWave")
        rt = cmd_parts[3] if len(cmd_parts) > 3 else Env.get("DEFAULT_RT", "Broadcasting")
        pi = cmd_parts[4] if len(cmd_parts) > 4 else Env.get("DEFAULT_PI", "FFFF")

        return (targets, frequency, ps, rt, pi)

def setup(reg):
    reg.register(LiveOp)