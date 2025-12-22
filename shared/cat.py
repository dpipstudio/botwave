import hashlib
import sys
from pathlib import Path

from .logger import Log

def check():
    # checks for system integrity, trust.
    # idea taken from netgoat-xyz/netgoat

    cat = "d059f219589886e03b176dac73081702"

    path = Path(__file__).resolve().parent / "cat.jpg"
    md5 = hashlib.md5()

    if path.exists():
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                md5.update(chunk)

        if md5.hexdigest() == cat:
            return # good

    # bad
    Log.error("BotWave integrity check failed. Did we lose our cat ?")
    sys.exit(1)