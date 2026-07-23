from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggest, Suggestion
from prompt_toolkit.history import FileHistory, InMemoryHistory
from prompt_toolkit.validation import Validator, ValidationError
import shlex


# commands are split into "server", "local", and "always" categories.
# server commands that need `<targets>` as a first arg need to have `targets=True`
# and no string in their syntax 
class Command():
    def __init__(self, syntax: str, targets: bool = False):
        self.__syntax = syntax
        self.__targets = targets
    
    @property
    def syntax(self):
        return self.__syntax
    
    def process_syntax(self):
        if self.__targets:
            self.__syntax = f"<targets> {self.__syntax}"

class SyntaxSuggester(AutoSuggest):
    def __init__(self, commands: dict):
        self.commands = commands
        super().__init__()

    def get_suggestion(self, buffer, document):
        text = document.text
        if not text:
            return None
        
        # no space yet = still typing the command name itself
        curr_text = text.lstrip()
        if " " not in curr_text and curr_text not in self.commands:
            matches = [name for name in self.commands if name.startswith(text)]
            if not matches:
                return None
            
            best = min(matches)
            return Suggestion(best[len(text):])

        try:
            parts = shlex.split(text)
            in_open_quote = False

        except ValueError:
            # probably an unclosed quote, try fixing it
            last_quote_idx = max(text.rfind('"'), text.rfind("'"))
            parseable = text[:last_quote_idx]

            try:
                parts = shlex.split(parseable)

            except ValueError:
                return None  #  give up
            
            in_open_quote = True

        if not parts:
            return None

        cmd = parts[0]
        if cmd not in self.commands:
            return None

        syntax_parts = self.commands[cmd].syntax.split(" ") if self.commands[cmd].syntax else []
        typed_args = parts[1:]

        remaining = syntax_parts[len(typed_args) if not in_open_quote else len(typed_args) + 1 :]

        if not remaining:
            return None

        return Suggestion(" " + " ".join(remaining))

class CommandValidator(Validator):
    def __init__(self, commands: dict):
        self.commands = commands
        super().__init__()

    def validate(self, document):
        text = document.text
        if not text:
            return

        try:
            parts = shlex.split(text)
        
        except ValueError:
            raise ValidationError(
                message=f"command is not properly formatted",
                cursor_position=len(text)
            )
        

        cmd = parts[0]

        if cmd not in self.commands:
            return

        syntax_parts = self.commands[cmd].syntax.split(" ") if self.commands[cmd].syntax else []
        typed_args = parts[1:]

        required = [p for p in syntax_parts if not p.startswith("[")]

        if len(typed_args) < len(required):
            missing = required[len(typed_args):]
            raise ValidationError(
                message=f"missing required values: {' '.join(missing)}",
                cursor_position=len(text)
            )

COMMANDS = {
    "server": {
        "list": Command(syntax=""),
        "sync": Command(syntax="<targets|folder/> <source_target|folder/>"),
        "kick": Command(syntax="[reason]", targets=True),
        "update": Command(syntax="[latest|<version>]", targets=True),
        "status": Command(syntax="[targets]") # targets are optional, so it needs to be taken apart
    },
    "local": {
        "status": Command(syntax="")
    },
    "always": {
        "start": Command(syntax="<file> [loop] [freq] [ps] [rt] [pi]", targets=True),
        "stop": Command(syntax="", targets=True),
        "queue": Command(syntax="queue [+|-|*|!|?]"),
        "live": Command(syntax="[freq] [ps] [rt] [pi]", targets=True),
        "sstv": Command(syntax="<image_path> [mode] [output_wav] [frequency] [loop] [ps] [rt] [pi]", targets=True),
        "morse": Command(syntax="<text|file> [wpm] [freq] [loop] [ps] [rt] [pi]", targets=True),
        "upload": Command(syntax="<file|folder>", targets=True),
        "dl": Command(syntax="<url>", targets=True),
        "lf": Command(syntax="", targets=True),
        "rm": Command(syntax="<filename|all>", targets=True),
        "handlers": Command(syntax="[filename]"),
        "<": Command(syntax="<command>"),
        "|": Command(syntax="<command>"),
        "get": Command(syntax="<keys|*>"),
        "set": Command(syntax="<key> <value> [immutable]"),
        "exit": Command(syntax=""),
        "help": Command(syntax="")
    }
}

def get_prompt(history_path: str, is_server: bool = True):

    commands = {}

    commands.update(COMMANDS["always"])
        
    if not is_server:
        commands.update(COMMANDS["local"])

    else:
        commands.update(COMMANDS["server"])

        for name, cmd in commands.items():
            cmd.process_syntax()

    try:
        history = FileHistory(history_path)
        list(history.load_history_strings()) # dont load (and crash) later on

    except (OSError, PermissionError):
        history = InMemoryHistory()

    return PromptSession(
        auto_suggest=SyntaxSuggester(commands=commands),
        validator=CommandValidator(commands=commands),
        validate_while_typing=False,
        history=history
    )

