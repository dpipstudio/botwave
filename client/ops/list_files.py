import json
from datetime import datetime
from pathlib import Path
from typing import Any

from shared.env import Env
from shared.logger import Log
from shared.ops import GeneralOp
from shared.protocol import Commands
from shared.protomanager import ParsedCommand

class ListFilesOp(GeneralOp):
    """
    The OP that handles Commands.LIST_FILES. Replies with a JSON
    containing information about every file inside of the upload dir.

    [
      {
        "name": "filename",
        "size": size_bytes,
        "modified": timestamp
      }
    ]
    """

    commands = {Commands.LIST_FILES: "list"}

    async def list(self, parsed: ParsedCommand):
        try:
            wav_files: list[dict[str, Any]] = []
            upload_dir = Path(Env.get("UPLOAD_DIR"))

            for file_path in upload_dir.iterdir():
                if file_path.suffix.lower() == '.wav' and file_path.is_file():

                    stat_info = file_path.stat()
                    wav_files.append({
                        'name': file_path.name,
                        'size': stat_info.st_size,
                        'modified': datetime.fromtimestamp(stat_info.st_mtime).isoformat()
                    })

            wav_files.sort(key=lambda x: x['name'])

            await self.owner.proto.reply(
                parsed,
                Commands.OK,
                message=f"Found {len(wav_files)} files",
                files=json.dumps(wav_files)
            )
            Log.file(f"Listed {len(wav_files)} files")

        except Exception as e:
            await self.owner.proto.reply(parsed, Commands.ERROR, message=str(e))

def setup(reg: Any):
    reg.register(ListFilesOp)