from pathlib import Path

from shared.env import Env
from shared.logger import Log
from shared.ops import CliOp

class ListFilesOp(CliOp):
    name = "lf"

    async def handle(self, is_cmd: bool = False, cmd_parts: str = None):
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

def setup(reg):
    reg.register(ListFilesOp)