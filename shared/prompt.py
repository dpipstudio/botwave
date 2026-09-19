import shlex
import re

from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggest, Suggestion
from prompt_toolkit.document import Document
from prompt_toolkit.history import FileHistory, InMemoryHistory
from prompt_toolkit.key_binding import KeyBindings, KeyPressEvent
from prompt_toolkit.validation import Validator, ValidationError
from typing import Any

COMMANDS: dict[str, str] = {}

# for autofill keybinds, only fill them for command names, not syntax
kb = KeyBindings()

@kb.add("tab")
@kb.add("right")
@kb.add("c-e")
@kb.add("escape", "f")
def handle_completion(event: KeyPressEvent):
    buffer = event.current_buffer
    suggestion = buffer.suggestion

    # only fill command names
    if suggestion and not isinstance(suggestion, SyntaxHint) and buffer.document.is_cursor_at_the_end:
        buffer.insert_text(suggestion.text)

    else:
        buffer.cursor_right()

class SyntaxHint(Suggestion):
    pass

class SyntaxSuggester(AutoSuggest):
    def __init__(self):
        super().__init__()

    def get_suggestion(self, _, document: Document):
        text = document.text

        if "#" in text:
            # ignore commented stuff
            text = text.split("#", 1)[0]

        if not text:
            return None
        
        # no space yet = still typing the command name itself
        curr_text = text.lstrip()
        if " " not in curr_text and curr_text not in COMMANDS:
            matches = [name for name in COMMANDS if name.startswith(text)]
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
        if cmd not in COMMANDS:
            return None

        syntax_parts = COMMANDS[cmd].strip().split(" ") if COMMANDS[cmd] else []
        typed_args = parts[1:]

        remaining = syntax_parts[len(typed_args) if not in_open_quote else len(typed_args) + 1 :]

        if not remaining:
            return None

        return SyntaxHint(" " + " ".join(remaining))

class CommandValidator(Validator):
    def __init__(self):
        super().__init__()

    def validate(self, document: Document):
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

        if cmd not in COMMANDS:
            return

        syntax = COMMANDS[cmd] if COMMANDS[cmd] else ""
        typed_args = parts[1:]

        required = re.findall(r'<[^>]*>', syntax)

        if len(typed_args) < len(required):
            missing = required[len(typed_args):]
            raise ValidationError(
                message=f"missing required values: {' '.join(missing)}",
                cursor_position=len(text)
            )


def get_prompt(commands: dict[str, str], history_path: str) -> PromptSession[Any]:
    COMMANDS.clear()
    COMMANDS.update(commands)
    
    try:
        # test if the file is  readable and writable
        with open(history_path, "a+b"):
            pass

        history = FileHistory(history_path)
        list(history.load_history_strings()) # dont load (and crash) later on

    except (OSError, PermissionError):
        history = InMemoryHistory()

    return PromptSession(
        auto_suggest=SyntaxSuggester(),
        validator=CommandValidator(),
        key_bindings=kb,
        validate_while_typing=False,
        history=history
    )

