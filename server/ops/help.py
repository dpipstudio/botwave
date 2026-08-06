from shared.logger import Log
from shared.ops import CliOp

class HelpOp(CliOp):
    name = "help"

    async def handle(self, is_cmd: bool = False, cmd_parts: list = []):
        Log.header("BotWave Server - Help")
        Log.section("Available Commands")

        Log.print("list", "bright_green")
        Log.print("  List all connected clients", "white")
        Log.print("  Example:", "white")
        Log.print("    list", "cyan")
        Log.print("")

        Log.print("start <targets> <file> [freq] [loop] [ps] [rt] [pi]", "bright_green")
        Log.print("  Start broadcasting on client(s)", "white")
        Log.print("  Example:", "white")
        Log.print("    start all broadcast.wav 100.5 MyRadio", "cyan")
        Log.print("")

        Log.print("stop <targets>", "bright_green")
        Log.print("  Stop broadcasting on client(s)", "white")
        Log.print("  Example:", "white")
        Log.print("    stop all", "cyan")
        Log.print("")

        Log.print("queue [+|-|*|!|?]", "bright_green")
        Log.print("  Manage broadcast queue", "white")
        Log.print("  Use 'queue ?' for detailed help", "white")
        Log.print("")

        Log.print("live <targets> [freq] [ps] [rt] [pi]", "bright_green")
        Log.print("  Start a live audio broadcast to client(s)", "white")
        Log.print("  Example:", "white")
        Log.print("    live all", "cyan")
        Log.print("")

        Log.print("sstv <targets> <image_path> [mode] [frequency] [loop] [ps] [rt] [pi]", "bright_green")
        Log.print("  Convert an image into a SSTV WAV file, and then broadcast it", "white")
        Log.print("  Example:", "white")
        Log.print("    sstv all /path/to/mycat.png Robot36 90 false PsPs Cutie FFFF", "cyan")
        Log.print("")

        Log.print("morse <targets> <text|file> [wpm] [freq] [loop] [ps] [rt] [pi]", "bright_green")
        Log.print("  Convert text to Morse code WAV and broadcast it", "white")
        Log.print("  Examples:", "white")
        Log.print("    morse all \"CQ CQ DE BOTWAVE\" 18 90 false BOTWAVE MORSE", "cyan")
        Log.print("    morse pi1 message.txt", "cyan")
        Log.print("")

        Log.print("upload <targets> <file|folder>", "bright_green")
        Log.print("  Upload a WAV file or a folder's files to client(s)", "white")
        Log.print("  Examples:", "white")
        Log.print("    upload all broadcast.wav", "cyan")
        Log.print("    upload pi1,pi2 /home/bw/lib", "cyan")
        Log.print("")

        Log.print("sync <targets|folder> <source_target|folder>", "bright_green")
        Log.print("  Synchronize files across clients or to/from local folders", "white")
        Log.print("  Examples:", "white")
        Log.print("    sync all pi1", "cyan")
        Log.print("    sync pi2,pi3 music", "cyan")
        Log.print("    sync backup/ pi1", "cyan")
        Log.print("")

        Log.print("dl <targets> <url> [destination]", "bright_green")
        Log.print("  Request client(s) to download a file from a URL", "white")
        Log.print("  Example:", "white")
        Log.print("    dl all http://example.com/file.wav", "cyan")
        Log.print("")

        Log.print("lf <targets>", "bright_green")
        Log.print("  List broadcastable files on client(s)", "white")
        Log.print("  Example:", "white")
        Log.print("    lf all", "cyan")
        Log.print("")

        Log.print("rm <targets> <filename|glob>", "bright_green")
        Log.print("  Remove a file from client(s)", "white")
        Log.print("  Example:", "white")
        Log.print("    rm all broadcast.wav", "cyan")
        Log.print("    rm all *", "cyan")
        Log.print("")

        Log.print("kick <targets> [reason]", "bright_green")
        Log.print("  Kick client(s) from the server", "white")
        Log.print("  Example:", "white")
        Log.print("    kick pi1 Maintenance", "cyan")
        Log.print("")

        Log.print("update <targets> [version]", "bright_green")
        Log.print("  Request client(s) to update and restart", "white")
        Log.print("  Omit version to update to the latest release", "white")
        Log.print("  Examples:", "white")
        Log.print("    update all", "cyan")
        Log.print("    update all v1.0.0-oak", "cyan")
        Log.print("")

        Log.print("handlers [filename]", "bright_green")
        Log.print("  List all handlers or commands in a specific handler file", "white")
        Log.print("  Example:", "white")
        Log.print("    handlers", "cyan")
        Log.print("")

        Log.print("< <command>", "bright_green")
        Log.print("  Run a shell command on the main OS", "white")
        Log.print("  Example:", "white")
        Log.print("    < df -h", "cyan")
        Log.print("")

        Log.print("| <command>", "bright_green")
        Log.print("  Run a shell command and pipe each output line as a BotWave command", "white")
        Log.print("  Example:", "white")
        Log.print("    | cat commands.txt", "cyan")
        Log.print("")

        Log.print("get <keys|*>", "bright_green")
        Log.print("  Get one or more environment variable(s)", "white")
        Log.print("  Use '*' to list all environment variables", "white")
        Log.print("  Examples:", "white")
        Log.print("    get PORT", "cyan")
        Log.print("    get PORT HOST FPORT", "cyan")
        Log.print("    get *", "cyan")
        Log.print("")

        Log.print("set <key> <value> [immutable]", "bright_green")
        Log.print("  Set an environment variable", "white")
        Log.print("  If immutable is 'true', the value cannot be changed without re-setting it as immutable. Editing those values is not recommended.", "white")
        Log.print("  Examples:", "white")
        Log.print("    set PROMPT_TEXT \"._.\"", "cyan")
        Log.print("    set PASSKEY mykey true", "cyan")
        Log.print("")

        Log.print("status [targets]", "bright_green")
        Log.print("  Show server status, and optionally the broadcast status of client(s)", "white")
        Log.print("  Examples:", "white")
        Log.print("    status", "cyan")
        Log.print("    status all", "cyan")
        Log.print("")

        Log.print("exit", "bright_green")
        Log.print("  Exit the application", "white")
        Log.print("  Example:", "white")
        Log.print("    exit", "cyan")
        Log.print("")

        Log.print("help", "bright_green")
        Log.print("  Display this help message", "white")
        Log.print("  Example:", "white")
        Log.print("    help", "cyan")
        Log.print("")

        custom_commands = self.owner.custom_commands.get_all()

        if custom_commands:
            Log.section("Custom Commands")

            for command in custom_commands:
                for line in command["help"]:
                    Log.print(line, style="yellow")

                Log.print("")

        Log.section("Targets")

        Log.print("'all' - All connected clients", "white")
        Log.print("client_id - Specific client by ID", "white")
        Log.print("hostname - Client by hostname", "white")
        Log.print("Comma-separated list - Multiple clients", "white")
        Log.print("Example:", "white")
        Log.print("  pi1,pi2", "cyan")
        Log.print("  all", "cyan")
        Log.print("  kitchen-pi", "cyan")

def setup(reg):
    reg.register(HelpOp)