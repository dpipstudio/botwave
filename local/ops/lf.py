from pathlib import Path
from typing import Any

from shared.dirutils import BW_PATH
from shared.env import Env
from shared.logger import Log
from shared.ops import CliOp

class ListFilesOp(CliOp):
    """
    The 'lf' command OP. Prints the files that the local
    client has in its upload folder. 
    """

    name = "lf"
    syntax = ""
    short_help = "List files in the upload directory"
    long_help = short_help
    examples = [
        "lf"
    ]
    env_vars = {
        "UPLOAD_DIR": (f"{BW_PATH}/uploads", "The upload directory path")
    }

    async def handle(self, is_cmd: bool = False, cmd_parts: list[str] = []):
        target_dir = Path(Env.get("UPLOAD_DIR"))

        try:
            files = [p.name for p in target_dir.iterdir() if p.is_file()]

            if not files:
                Log.info(f"No files found in the directory {target_dir}")
                return
            
            Log.info(f"Files in directory {target_dir}:")

            for file in files:
                Log.print(f"  {file}", 'white')

        except Exception as e:
            Log.error(f"Error listing files: {e}")

def setup(reg: Any):
    reg.register(ListFilesOp)