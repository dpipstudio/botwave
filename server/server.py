import argparse
import asyncio
from datetime import datetime
from pathlib import Path
from prompt_toolkit.formatted_text import ANSI
from prompt_toolkit.patch_stdout import patch_stdout
import re
import shlex
import sys
import traceback
from typing import Dict, List, Optional

# using this to access to the shared dir files
sys.path.append(str(Path(__file__).resolve().parent.parent))

from shared.alsa import Alsa
from shared.cat import check
from shared.custom_cmds import CCMD
from shared.env import Env
from shared.handlers import HandlerExecutor
from shared.logger import Log
from shared.ops import CliOp
from shared.prompt import get_prompt
from shared.protocol import Commands, ProtocolParser, PROTOCOL_VERSION
from shared.queue import Queue
from shared.registry import Registry, UpperException
from shared.tips import TipEngine
from shared.version import check_for_updates
from shared.ws_cmd import WSCMDH

class BotWaveServer:
    def __init__(self):
        self.registry = Registry(self)
        self.clients: Dict[str, object] = {}
        self.ws_server = None
        self.http_server = None
        self.alsa = Alsa()
        self.running = False
        self.queue = Queue(self)
        self.tips = TipEngine()
        self.handlers_executor = HandlerExecutor(self.cmd_exec)
        self.custom_commands = CCMD(is_server=True)
        self.last_argv = []
        self.rc_clients = 0
        self.ws_handler = None

    def parse_targets(self, targets: str) -> List[str]:
        if not targets:
            Log.error("No targets specified")
            return []

        if targets.lower() == 'all':
            return list(self.clients.keys())

        target_list = [t.strip() for t in targets.split(',')]
        valid_targets = []

        for target in target_list:
            if target in self.clients:
                valid_targets.append(target)

            else:
                found = False

                for client_id, client in self.clients.items():
                    if client.machine_info.get('hostname') == target:
                        valid_targets.append(client_id)
                        found = True
                        break

                if not found:
                    Log.error(f"Client '{target}' not found")

        return valid_targets

    async def handle_message(self, client_id: Optional[str], message: str, websocket):
        try:
            Log.debug(f"{client_id}: {message}")

            parsed = ProtocolParser.parse_command(message)
            cmd = parsed['command']

            if cmd not in vars(Commands).values():
                return

            if client_id is None and cmd not in [Commands.REGISTER, Commands.AUTH, Commands.VER]:
                Log.warning(f"Got an unexpected command during registration: {cmd}")

                error = ProtocolParser.build_response(
                    Commands.ERROR,
                    f"Expected {Commands.REGISTER}, {Commands.AUTH}, or {Commands.VER}, got {cmd}"
                )
                await websocket.send(error)
                await websocket.close()
                return

            if client_id in self.clients:
                self.clients[client_id].last_seen = datetime.now()

                if self.clients[client_id].proto.dispatch(parsed):
                    return

            found = await self.registry.dispatch(
                cmd,
                client_id=client_id,
                parsed=parsed,
                websocket=websocket
            )

            if not found:
                Log.warning(f"Unexpected command from {client_id}: {cmd}")

                if client_id in self.clients:
                    self.clients[client_id].proto.reply(
                        parsed,
                        Commands.ERROR,
                        message=f"Unknown command: {cmd}. Perhaps a protocol mismatch?"
                    )

        except Exception as e:
            Log.error(f"Error handling message from {client_id}: {e}")

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
                return

            try:
                cmd_parts = shlex.split(command)

            except ValueError as e:
                Log.error(f"Invalid command syntax: {e}")
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

    async def client_connect(self, client_id: str, websocket):
        return

    async def client_disconnect(self, client_id: str):
        if client_id in self.clients:
            client = self.clients[client_id]
            Log.warning(f"Client disconnected: {client.get_display_name()}")

            await self.registry.dispatch("handlers_ondisconnect", client_id=client_id)
            del self.clients[client_id]

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

def fail_banner():
    style = "bold rgb(200,0,0)"

    Log.print("+------------------------------------------------------------+", style)
    Log.print("|                                                            |", style)
    Log.print("|  Server failed to start.                                   |", style)
    Log.print("|                                                            |", style)
    Log.print("|  If there is a stack trace above, please provide it        |", style)
    Log.print("|  when opening an issue.                                    |", style)
    Log.print("|                                                            |", style)
    Log.print("|  If you do not know what is happening, please open an      |", style)
    Log.print("|  issue on GitHub:                                          |", style)
    Log.print("|                                                            |", style)
    Log.print("|  https://github.com/dpipstudio/botwave/issues/new/         |", style)
    Log.print("|                                                            |", style)
    Log.print("+------------------------------------------------------------+", style)


async def main():
    Log.header("BotWave Server")

    check()

    parser = argparse.ArgumentParser(prog="bw-server", description='BotWave Server')
    parser.add_argument('--host', default=None, help='Server host')
    parser.add_argument('--port', type=int, default=None, help='Server port')
    parser.add_argument('--fport', type=int, default=None, help='File transfer (HTTP) port')
    parser.add_argument('--pk', help='Passkey for authentication')
    parser.add_argument('--handlers-dir', default=None, help='Directory to retrieve s_ handlers from')
    parser.add_argument('--start-asap', action=argparse.BooleanOptionalAction, default=None, dest='start_asap', help='Start broadcasts immediately (may cause client desync)')
    parser.add_argument('--skip-checks', action=argparse.BooleanOptionalAction, default=None, help='Skip system requirements checks')
    parser.add_argument('--rc', type=int, default=None, help='Remote CLI port for remote management')
    parser.add_argument('--config', type=str, help='Path to a config file to load into environment')
    parser.add_argument('--daemon', action=argparse.BooleanOptionalAction, help='Run in non-interactive daemon mode')
    args = parser.parse_args()

    if args.config:
        Env.load(args.config) # will silently drop if file doesn't exist

    set_prio("HOST", args.host, '0.0.0.0', immutable=True)
    set_prio("PORT", args.port, 9938, immutable=True)
    set_prio("FPORT", args.fport, 9921, immutable=True)
    set_prio("HANDLERS_DIR", args.handlers_dir, '/opt/BotWave/handlers/')
    set_prio("SKIP_CHECKS", args.skip_checks, False)
    set_prio("DAEMON", args.daemon, False, immutable=True)
    set_prio("REMOTE_CMD_PORT", args.rc, None, immutable=True)
    set_prio("PASSKEY", args.pk, None, immutable=True)
    set_prio("HISTORY_PATH", None, "/opt/BotWave/.history")
    set_prio("PROMPT_TEXT", None, "botwave › ")
    set_prio("EXTRA_ALLOWED_DIRS", None, str(Path.cwd()))

    if args.start_asap is not None:
        Env.set("WAIT_START", str(not args.start_asap))

    elif not Env.get("WAIT_START", False):
        Env.set("WAIT_START", str(True))  

    server = BotWaveServer()
    server.registry.from_dir(Path(__file__).resolve().parent / "ops")

    try:
        # server startup
        server.tips.start()

        await server.registry.dispatch("server_startup")
        server.running = True

        if not Env.get_bool("SKIP_CHECKS"):
            check_updates()

        Log.server("BotWave Server started")
        Log.version(f"Protocol Version: {PROTOCOL_VERSION}")

        if Env.get("PASSKEY"):
            Log.auth("Server is using authentication with a passkey")

        if Env.get("REMOTE_CMD_PORT"):
            server.ws_handler = WSCMDH(
                command_executor=server.cmd_exec,
                registry=server.registry
            )
            
            server.ws_handler.start()

        await server.registry.dispatch("handlers_onready")

    except Exception as e:
        Log.error(f"Startup error: {e}")

        if Env.get_bool("TALK"):
            traceback.print_exc()

        fail_banner()
        return

    if Env.get_bool("DAEMON"):
        Log.info("Running in daemon mode. The server will continue to run in the background.")
        try:
            while server.running:
                await asyncio.sleep(1)
                
        except (KeyboardInterrupt, asyncio.CancelledError):
            Log.warning("^C received, shutting down...")
            await server.registry.dispatch("exit")

        except UpperException:
            return

        return

    prompt = get_prompt(
        commands={op.name: op.syntax for op in server.registry.get_instances() if isinstance(op, CliOp)},
        history_path=Env.get("HISTORY_PATH", "/opt/BotWave/.history")
        )

    Log.print("Type 'help' for commands", 'bright_yellow')

    with patch_stdout(raw=True):
        Log._stream = sys.stdout

        while server.running:
            try:
                print()
                cmd_input = (await prompt.prompt_async(ANSI(f"\033[1;32m{Env.get('PROMPT_TEXT')}\033[0m"))).strip()

                if not cmd_input:
                    continue

                await server.cmd_exec(cmd_input)

            except (KeyboardInterrupt, asyncio.CancelledError):
                Log.warning("Use 'exit' to exit")

            except EOFError:
                try:
                    await server.registry.dispatch("exit")

                except UpperException:  # omfg i need  to put this everywhere
                    return

            except UpperException:
                return
            
            except Exception as e:
                Log.error(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())