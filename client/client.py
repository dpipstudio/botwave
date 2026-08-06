#!/opt/BotWave/venv/bin/python3
# This path won't be correct if you didn't use the https://botwave.dpip.lol/install installer or similar.

# BotWave Client
# https://github.com/dpipstudio/botwave
# https://botwave.dpip.lol
# A DPIP Studio project. https://dpip.lol
# Licensed under GPL-v3.0 (see LICENSE)

import argparse
import asyncio
from pathlib import Path
import sys

# using this to access to the shared dir files
sys.path.append(str(Path(__file__).resolve().parent.parent))

from shared.alsa import Alsa
from shared.cat import check
from shared.env import Env
from shared.logger import Log
from shared.protocol import Commands, ProtocolParser
from shared.pw_monitor import PWM
from shared.registry import Registry, UpperException
from shared.syscheck import check_requirements
from shared.tips import TipEngine
from shared.version import check_for_updates

class BotWaveClient:
    """
    The BotWave Client. Holds the core shared
    states and components needed for the app runtime.
    """

    def __init__(self):
        # connection state
        self.client_id = None
        self.http_client = None
        self.proto = None
        self.registered = False
        self.running = False
        self.ws_client = None

        # broadcast state
        self.broadcast_start_time = None
        self.broadcasting = False
        self.current_file = None
        self.feed_task = None
        self.piwave = None
        self.stream_active = False
        self.stream_task = None

        # helpers
        self.alsa = Alsa()
        self.piwave_monitor = PWM()
        self.registry = Registry(self)
        self.tips = TipEngine(is_server=False)

    async def handle_message(self, message: str):
        Log.debug(message)

        parsed = ProtocolParser.parse_command(message)
        cmd = parsed['command']

        if cmd not in vars(Commands).values():
            found = False

        else:
            try:
                found = await self.registry.dispatch(cmd, parsed=parsed)

            except UpperException:
                # upperexception: stop request, dont ask why
                await self.ws_client.disconnect()
                return
        
        if not found:
            Log.warning(f"Unknown command: {cmd}")
            await self.proto.reply(parsed, Commands.ERROR, message=f"Unknown command: {cmd}. Perhaps a protocol mismatch?")


# startup helpers
def set_prio(key, cli_value, default, immutable=False):
    if cli_value is not None:
        Env.set(key, str(cli_value), immutable=immutable)

    elif not Env.get(key, False) and default is not None:
        Env.set(key, str(default), immutable=immutable)

def check_updates():
    Log.info("Checking for software updates...")

    try:
        latest_proto_ver, latest_ver = check_for_updates()

        if latest_proto_ver:
            Log.update(f"A protocol update is available. Latest version: {latest_proto_ver}")
            Log.update("It is recommended updating to the latest version by running 'bw-update' in your shell")

        elif latest_ver:
            Log.update(f"A newer version of BotWave is available ({latest_ver})")
            Log.update(f"Update by running 'bw-update --to {latest_ver}' in your shell")

        else:
            Log.success("You are using the latest version")

    except Exception as e:
        Log.warning("Unable to check for updates (continuing anyway)")

# entry point
async def main():
    Log.header("BotWave Client")

    check()

    parser = argparse.ArgumentParser(prog="bw-client", description='BotWave Client')
    parser.add_argument('server_host', nargs='?', help='Server hostname/IP')
    parser.add_argument('--port', type=int, default=None, help='Server port')
    parser.add_argument('--fhost', help='File transfer server hostname/IP (defaults to server_host)')
    parser.add_argument('--fport', type=int, default=None, help='File transfer (HTTP) port')
    parser.add_argument('--upload-dir', default=None, help='Uploads directory')
    parser.add_argument('--pk', help='Passkey for authentication')
    parser.add_argument('--skip-checks', dest='skip_checks', action=argparse.BooleanOptionalAction, default=None, help='Skip update and requirements checks')
    parser.add_argument('--talk', action=argparse.BooleanOptionalAction, default=None, help='Makes PiWave (broadcast manager) output logs visible.')
    parser.add_argument('--config', type=str, help='Path to a config file to load into environment')
    args = parser.parse_args()

    if args.config:
        Env.load(args.config) # will silently drop if file doesn't exist

    if args.server_host:
        Env.set("SERVER_HOST", args.server_host, immutable=True)
        
    elif not Env.get("SERVER_HOST", False):
        try:
            Env.set("SERVER_HOST", input("Server hostname/IP: ").strip(), immutable=True)

        except Exception:
            return

    set_prio("SERVER_PORT", args.port, 9938, immutable=True)
    set_prio("FHOST", args.fhost, Env.get("SERVER_HOST"), immutable=True)
    set_prio("FPORT", args.fport, 9921, immutable=True)
    set_prio("UPLOAD_DIR", args.upload_dir, '/opt/BotWave/uploads/')
    set_prio("TALK", args.talk, False)
    set_prio("SKIP_CHECKS", args.skip_checks, False)

    if args.pk:
        Env.set("PASSKEY", args.pk, immutable=True)

    if not Env.get_bool("SKIP_CHECKS"):
        check_requirements()
        check_updates()


    client = BotWaveClient()
    client.registry.from_dir(Path(__file__).resolve().parent / "ops")
    
    try:
        await client.registry.dispatch("client_connect")

    except UpperException:
        await client.ws_client.disconnect() # if we get a reg to

    client.running = True
    client.tips.start()

    try:
        await client.ws_client.wait_for_disconnect()

    except (KeyboardInterrupt, asyncio.CancelledError):
        Log.warning("Shutting down...")

    except Exception as e:
        Log.error(f"Error: {e}")

    finally:
        await client.registry.dispatch("client_stop")

if __name__ == "__main__":
    asyncio.run(main())