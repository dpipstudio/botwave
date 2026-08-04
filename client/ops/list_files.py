from datetime import datetime
import json
from pathlib import Path

from shared.env import Env
from shared.logger import Log
from shared.ops import GeneralOp
from shared.protocol import Commands

class ListFilesOp(GeneralOp):
    commands = {Commands.LIST_FILES: "list"}

    async def list(self, parsed):
        try:
            wav_files = []
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

def setup(reg):
    reg.register(ListFilesOp)