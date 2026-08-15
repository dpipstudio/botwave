#!/opt/BotWave/venv/bin/python3
# This path won't be correct if you didn't use the https://botwave.dpip.lol/install installer or similar.

# BotWave Local Client
# https://github.com/dpipstudio/botwave
# https://botwave.dpip.lol
# A DPIP Studio project. https://dpip.lol
# Licensed under GPL-v3.0 (see LICENSE)

import argparse
import asyncio
from pathlib import Path
from prompt_toolkit.formatted_text import ANSI
from prompt_toolkit.patch_stdout import patch_stdout
import re
import shlex
import sys

# using this to access to the shared dir files
sys.path.append(str(Path(__file__).resolve().parent.parent))

from shared.alsa import Alsa
from shared.cat import check
from shared.custom_cmds import CCMD
from shared.dirutils import BW_PATH
from shared.env import Env
from shared.handlers import HandlerExecutor
from shared.logger import Log
from shared.ops import CliOp
from shared.prompt import get_prompt
from shared.pw_monitor import PWM
from shared.queue import Queue
from shared.registry import Registry, UpperException
from shared.syscheck import check_requirements
from shared.tips import TipEngine
from shared.version import check_for_updates
from shared.ws_cmd import WSCMDH

class BotWaveLocal:
    """
    The BotWave Local client. Holds the core shared
    states and components needed for the app runtime.
    """

    def __init__(self):
        # broadcast state
        self.broadcast_start_time = None
        self.broadcasting = False
        self.current_file = None
        self.piwave = None
        self.piwave_monitor = PWM()

        # core systems
        self.alsa = Alsa()
        self.custom_commands = CCMD(is_server=False)
        self.handlers_executor = HandlerExecutor(self.cmd_exec)
        self.queue = Queue(client_instance=self, is_local=True)
        self.registry = Registry(self)
        self.tips = TipEngine(is_server=False)

        # remote control
        self.rc_clients = 0
        self.ws_handler = None

        # runtime / misc
        self.last_argv = []
        self.running = False

    async def cmd_exec(self, command: str, interpolate: bool = True):
        try:
            tx_match = re.search(r'transaction_id=([^\s]+)', command)
            if tx_match:
                Log.set_transaction_id(tx_match.group(1))
                command = re.sub(r'\s*transaction_id=[^\s]+', '', command)
            else:
                Log.clear_transaction_id()

            if "#" in command:
                command = command.split("#", 1)[0]

            command = command.strip()

            if interpolate:
                command = re.sub( # replace every {var} with the env value, if exists. if not, empty it
                    r'\{(\w+)\}',
                    lambda m: Env.get(m.group(1), ''),
                    command
                )

            if not command:
                Log.end()
                return

            try:
                cmd_parts = shlex.split(command)

            except ValueError as e:
                Log.error(f"Invalid command syntax: {e}")
                Log.end()
                return

            self.last_argv = cmd_parts

            cmd = cmd_parts[0].lower()
            cmd_parts.pop(0)

            found = await self.registry.dispatch(cmd, is_cmd=True, cmd_parts=cmd_parts)

            if not found:
                            
                if self.custom_commands.exists(cmd):
                    
                    await self.handlers_executor.execute_handler(
                        Path(Env.get("HANDLERS_DIR")) / f"{cmd}.cmd",
                        next(inst for inst in self.registry.get_instances() if type(inst).__name__ == "HandlersEventsOp").build_context(), # This has to be the worst line of code I ever wrote
                        silent=True
                        )

                else:                
                    Log.error(f"Unknown command: {cmd}")

        except UpperException:
            raise

        except Exception as e:
            Log.error(f"Error executing command '{command}': {e}")

        finally:
            Log.end()
            Log.clear_transaction_id()

# startup helpers
def set_prio(key, cli_value, default, immutable=False):
    if cli_value is not None:
        Env.set(key, str(cli_value), immutable=immutable)

    elif not Env.get(key, False) and default is not None:
        Env.set(key, str(default), immutable=immutable)

def check_updates():
    Log.info("Checking for software updates...")

    try:
        _, latest_ver = check_for_updates()

        if latest_ver:
            Log.update(f"A newer version of BotWave is available ({latest_ver})")
            Log.update(f"Update by running 'bw-update --to {latest_ver}' in your shell")

        else:
            Log.success("You are using the latest version")

    except Exception as e:
        Log.warning("Unable to check for updates (continuing anyway)")

# Entry point
async def main():
    Log.header("BotWave Local Client")

    check() # from shared.cat

    parser = argparse.ArgumentParser(prog="bw-local", description='BotWave Local Client')
    parser.add_argument('--upload-dir', default=None, help='Directory to store uploaded files')
    parser.add_argument('--handlers-dir', default=None, help='Directory to retrieve l_ handlers from')
    parser.add_argument('--skip-checks', action=argparse.BooleanOptionalAction, help='Skip system requirements checks')
    parser.add_argument('--daemon', action=argparse.BooleanOptionalAction, help='Run in daemon mode (non-interactive)')
    parser.add_argument('--rc', type=int, default=None, help='Remote CLI port for remote management')
    parser.add_argument('--pk', help='Optional passkey for remote management authentication')
    parser.add_argument('--talk', action=argparse.BooleanOptionalAction, help='Show debug logs')
    parser.add_argument('--config', type=str, help='Path to a config file to load into environment')
    args = parser.parse_args()

    if args.config:
        Env.load(args.config)

    set_prio("UPLOAD_DIR", args.upload_dir, str(Path(BW_PATH) / "uploads"))
    set_prio("HANDLERS_DIR", args.handlers_dir, str(Path(BW_PATH) / "handlers"))
    set_prio("SKIP_CHECKS", args.skip_checks, False)
    set_prio("DAEMON", args.daemon, False, immutable=True)
    set_prio("HOST", None, "0.0.0.0", immutable=True)
    set_prio("HISTORY_PATH", None, str(Path(BW_PATH) / ".history"))
    set_prio("PROMPT_TEXT", None, "botwave › ")
    set_prio("TALK", args.talk, False)
    set_prio("PASSKEY", args.pk, None, immutable=True)
    set_prio("REMOTE_CMD_PORT", args.rc, None, immutable=True)

    if not Env.get_bool("SKIP_CHECKS"):
        check_requirements()
        check_updates()

    local = BotWaveLocal()
    local.registry.from_dir(Path(__file__).resolve().parent / "ops")

    local.running = True #TODO: Check if this running attr is really useful

    if Env.get("REMOTE_CMD_PORT"):
        local.ws_handler = WSCMDH(
            command_executor=local.cmd_exec,
            registry=local.registry
        )
        
        local.ws_handler.start()

    local.tips.start()

    await local.registry.dispatch("handlers_onready")

    if Env.get_bool("DAEMON"):
        Log.info("Running in daemon mode. The local client will continue to run in the background.")
        try:
            while local.running:
                await asyncio.sleep(1)
                
        except (KeyboardInterrupt, asyncio.CancelledError):
            Log.warning("^C received, shutting down...")
            try:
                await local.registry.dispatch("exit")

            except UpperException:
                pass

        except UpperException:
            return

        return # to be sure to exit

    prompt = get_prompt(
        commands={op.name: op.syntax for op in local.registry.get_instances() if isinstance(op, CliOp)},
        history_path=Env.get("HISTORY_PATH")
        )

    Log.print("Type 'help' for commands", 'bright_yellow')

    with patch_stdout(raw=True):
        Log._stream = sys.stdout

        while local.running:
            try:
                print()
                cmd_input = (await prompt.prompt_async(ANSI(f"\033[1;32m{Env.get('PROMPT_TEXT')}\033[0m"))).strip()

                if not cmd_input:
                    continue

                await local.cmd_exec(cmd_input)

            except (KeyboardInterrupt, asyncio.CancelledError):
                Log.warning("Use 'exit' to exit")

            except EOFError:
                try:
                    await local.registry.dispatch("exit")

                except UpperException:  # omfg i need  to put this everywhere
                    return

            except UpperException:
                return
            
            except Exception as e:
                Log.error(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
    