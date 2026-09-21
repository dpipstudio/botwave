import tempfile
from pathlib import Path

BW_PATH = str(Path(__file__).resolve().parent.parent)
BW_TMP = str(Path(tempfile.gettempdir()) / "botwave")

# create the tempdir if it doesn't exist
try:
    tmp = Path(BW_TMP)
    tmp.mkdir(parents=True, exist_ok=True)
    tmp.chmod(0o1777)

except (PermissionError, OSError):
    pass