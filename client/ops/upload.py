from typing import Any

from shared.env import Env
from shared.logger import Log
from shared.ops import GeneralOp
from shared.protocol import Commands, ParsedCommand
from shared.security import PathValidator, SecurityError

class UploadOp(GeneralOp):
    """
    The OP handling Commands.UPLOAD_TOKEN. uploads a file 
    from the upload dir to the file server (https://FHOST:FPORT).
    """

    commands = {Commands.UPLOAD_TOKEN: "upload"}   

    async def upload(self, parsed: ParsedCommand):
        kwargs = parsed["kwargs"]

        token = kwargs.get('token')
        filename = kwargs.get('filename')
        size = int(kwargs.get('size', 0))

        if not token or not filename:
            await self.owner.proto.reply(
                parsed,
                Commands.ERROR,
                message="Missing token or filename"
            )
            return

        Log.file(f"Received upload token for: {filename} ({size if size > 0 else '?'} bytes)")

        try:
            filename = PathValidator.sanitize_filename(filename)
            filepath = PathValidator.safe_join(Env.get("UPLOAD_DIR"), filename)

        except SecurityError as e:
            Log.error(f"Invalid filename from server: {e}")
            await self.owner.proto.reply(
                parsed,
                Commands.ERROR,
                message="Provided filename raised a security violation"
            )
            return

        def progress(bytes_sent: int, total: int):
            if total > 0:
                Log.progress_bar(bytes_sent, total, prefix=f'Uploading {filename}:', suffix='Complete', style='yellow', icon='FILE', auto_clear=(bytes_sent == total))

        success = await self.owner.http_client.upload_file(
            server_host=Env.get("FHOST"),
            server_port=Env.get_int("FPORT"),
            token=token,
            filepath=filepath,
            progress_callback=progress
        )

        if success:
            Log.success(f"Upload completed: {filename}")
            await self.owner.proto.reply(
                parsed,
                Commands.OK,
                message=f"Uploaded {filename}"
            )

        else:
            Log.error(f"Upload failed: {filename}")
            await self.owner.proto.reply(
                parsed,
                Commands.ERROR,
                message="Upload failed"
            )

def setup(reg: Any):
    reg.register(UploadOp)