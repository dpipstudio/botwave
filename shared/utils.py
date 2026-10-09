import traceback
from typing import Any

from shared.env import Env
from shared.logger import Log

# for cli / env vars. cli > env > default
def set_prio(key: str, cli_value: Any | None, default: Any | None, immutable: bool = False):
    if cli_value is not None:
        Env.set(key, str(cli_value), immutable=immutable)

    elif not Env.get(key, False) and default is not None:
        Env.set(key, str(default), immutable=immutable)


def crashout(component: str, exeption: BaseException):
    style = "bold rgb(200,0,0)"

    message = f"BotWave {component} had a fatal error."

    Log.print(f"+------------------------------------------------------------+", style)
    Log.print(f"|                                                            |", style)
    Log.print(f"|{message:^60}|", style)
    Log.print(f"|                                                            |", style)
    Log.print(f"|  This is an error on our side and shouldn't be happening.  |", style)
    Log.print(f"|  Please open an issue on GitHub:                           |", style)
    Log.print(f"|                                                            |", style)
    Log.print(f"|  https://github.com/dpipstudio/botwave/issues/new/         |", style)
    Log.print(f"|                                                            |", style)
    Log.print(f"+------------------------------------------------------------+", style)

    if Env.get_bool("TALK"):
        Log.debug("Full trace:")
        traceback.print_exception(exeption)

    else:
        Log.print(f"{type(exeption).__name__}: {exeption}", "red")