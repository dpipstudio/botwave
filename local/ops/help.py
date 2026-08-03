from shared.logger import Log
from shared.ops import CliOp

class HelpOp(CliOp):
    name = "help"

    async def handle(self, is_cmd: bool = False, cmd_parts: list = []):
        Log.header("BotWave Local Client - Help")
        Log.section("Available Commands")

        Log.print("start <file> [frequency] [loop] [ps] [rt] [pi]", "bright_green")
        Log.print("  Start broadcasting a WAV file", "white")
        Log.print("  Example:", "white")
        Log.print("    start broadcast.wav 100.5 true MyRadio \"My Radio Text\" FFFF", "cyan")
        Log.print("")

        Log.print("stop", "bright_green")
        Log.print("  Stop the current broadcast", "white")
        Log.print("  Example:", "white")
        Log.print("    stop", "cyan")
        Log.print("")

        Log.print("live [freq] [ps] [rt] [pi]", "bright_green")
        Log.print("  Start a live audio broadcast", "white")
        Log.print("  Example:", "white")
        Log.print("    live", "cyan")
        Log.print("")

        Log.print("queue [+|-|*|!|?]", "bright_green")
        Log.print("  Manage broadcast queue", "white")
        Log.print("  Use 'queue ?' for detailed help", "white")
        Log.print("")

        Log.print("sstv <image_path> [mode] [frequency] [loop] [ps] [rt] [pi]", "bright_green")
        Log.print("  Convert an image into a SSTV WAV file, and then broadcast it", "white")
        Log.print("  Generated WAVs are cached, so re-running with the same image/mode won't regenerate", "white")
        Log.print("  Example:", "white")
        Log.print("    sstv /path/to/mycat.png Robot36 90 false PsPs Cutie FFFF", "cyan")
        Log.print("")

        Log.print("morse <text|file> [wpm] [frequency] [loop] [ps] [rt] [pi]", "bright_green")
        Log.print("  Convert text to Morse code WAV and broadcast it", "white")
        Log.print("  Examples:", "white")
        Log.print("    morse \"CQ CQ DE BOTWAVE\" 18 90 false BOTWAVE MORSE", "cyan")
        Log.print("    morse message.txt", "cyan")
        Log.print("")

        Log.print("lf", "bright_green")
        Log.print("  List files in the upload directory", "white")
        Log.print("")

        Log.print("rm <filename|glob>", "bright_green")
        Log.print("  Remove a file", "white")
        Log.print("  Example:", "white")
        Log.print("    rm broadcast.wav", "cyan")
        Log.print("    rm *.wav", "cyan")
        Log.print("")

        Log.print("upload <file|folder>", "bright_green")
        Log.print("  Upload a file or folder to the upload directory", "white")
        Log.print("  Examples:", "white")
        Log.print("    upload broadcast.wav", "cyan")
        Log.print("    upload /home/bw/lib", "cyan")
        Log.print("")

        Log.print("dl <url> [destination]", "bright_green")
        Log.print("  Download a WAV file from a URL", "white")
        Log.print("  Example:", "white")
        Log.print("    download http://example.com/file.wav myfile.wav", "cyan")
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
        Log.print("    get PORT HOST REMOTE_CMD_PORT", "cyan")
        Log.print("    get *", "cyan")
        Log.print("")

        Log.print("set <key> <value> [immutable]", "bright_green")
        Log.print("  Set an environment variable", "white")
        Log.print("  If immutable is 'true', the value cannot be changed without re-setting it as immutable. Editing those values is not recommended.", "white")
        Log.print("  Examples:", "white")
        Log.print("    set PROMPT_TEXT \"._.\"", "cyan")
        Log.print("    set PASSKEY mykey true", "cyan")
        Log.print("")

        Log.print("status", "bright_green")
        Log.print("  Show current broadcast and remote status", "white")
        Log.print("")

        Log.print("exit", "bright_green")
        Log.print("  Exit the application", "white")
        Log.print("  Example:", "white")
        Log.print("    exit", "cyan")

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

def setup(reg):
    reg.register(HelpOp)