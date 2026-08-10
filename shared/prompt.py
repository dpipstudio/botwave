from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggest, Suggestion
from prompt_toolkit.history import FileHistory, InMemoryHistory
from prompt_toolkit.validation import Validator, ValidationError
import shlex

class SyntaxSuggester(AutoSuggest):
    def __init__(self, commands: dict):
        self.commands = commands
        super().__init__()

    def get_suggestion(self, buffer, document):
        text = document.text

        if "#" in text:
            # ignore commented stuff
            text = text.split("#", 1)[0]

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

        syntax_parts = self.commands[cmd].split(" ") if self.commands[cmd] else []
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

        syntax_parts = self.commands[cmd].split(" ") if self.commands[cmd] else []
        typed_args = parts[1:]

        required = [p for p in syntax_parts if not p.startswith("[")]

        if len(typed_args) < len(required):
            missing = required[len(typed_args):]
            raise ValidationError(
                message=f"missing required values: {' '.join(missing)}",
                cursor_position=len(text)
            )


def get_prompt(commands: dict, history_path: str):

    try:
        # test if the file is  readable and writable
        with open(history_path, "a+b"):
            pass

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

