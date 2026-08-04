import asyncio
from pathlib import Path
import tempfile
import urllib.request

from shared.converter import Converter, SUPPORTED_EXTENSIONS
from shared.env import Env
from shared.logger import Log
from shared.ops import GeneralOp
from shared.protocol import Commands, PROTOCOL_VERSION
from shared.security import PathValidator, SecurityError

class DownloadUrlOp(GeneralOp):
    commands = {Commands.DOWNLOAD_URL: "download_url"}

    async def download_url(self, parsed):
        kwargs = parsed["kwargs"]

        url = kwargs.get('url')
        filename = kwargs.get('filename')

        if not url or not filename:
            await self.owner.proto.reply(
                parsed,
                Commands.ERROR,
                message="Missing URL or filename"
            )
            return

        try:
            filename = PathValidator.sanitize_filename(filename)
            filepath = PathValidator.safe_join(Env.get("UPLOAD_DIR"), str(Path(filename).with_suffix(".wav")))

        except SecurityError as e:
            Log.error(f"Invalid filename from server: {e}")
            
            await self.owner.proto.reply(
                parsed,
                Commands.ERROR,
                message="Provided filename raised a security violation"
            )
            return

        ext = Path(filename).suffix.lower().lstrip(".")
        converted = False

        try:
            Log.file(f"Downloading from URL: {url}")

            loop = asyncio.get_event_loop()

            if ext == "wav":
                await loop.run_in_executor(None, self.download, url, filepath)

            elif ext in SUPPORTED_EXTENSIONS:
                with tempfile.NamedTemporaryFile(delete=False, suffix="." + ext) as tmp:
                    tmp_path = tmp.name

                try:
                    await loop.run_in_executor(None, self.download, url, tmp_path)
                    Converter.convert_wav(tmp_path, filepath, Env.get_bool("TALK"))

                finally:
                    converted = True

                    if Path(tmp_path).is_file():
                        Path(tmp_path).unlink()

            else:
                raise ValueError(f"Unsupported file type from URL: .{ext}")

            if Path(filepath).is_file():
                file_size = Path(filepath).stat().st_size
        
                Log.success(f"Downloaded: {filename} ({file_size if file_size > 0 else '?'} bytes{', converted' if converted else ''})")

                await self.owner.proto.reply(
                    parsed,
                    Commands.OK,
                    message=f"Downloaded {filename}{' (converted)' if converted else ''}"
                )

            else:
                Log.error("Download failed: file not created")

                await self.owner.proto.reply(
                    parsed,
                    Commands.ERROR,
                    message="File not created"
                )

        except urllib.error.URLError as e:
            Log.error(f"Network error: {e}")
            await self.owner.proto.reply(
                parsed,
                Commands.ERROR,
                message=f"Network error: {e}"
            )

        except Exception as e:
            Log.error(f"Download failed: {e}")
            await self.owner.proto.reply(
                parsed,
                Commands.ERROR,
                message=f"Error: {e}"
            )


    def download(self, url, dest_path):
        headers = {
            "User-Agent": Env.get("DOWNLOAD_UA", f"BotWaveDownloads/{PROTOCOL_VERSION} (+https://github.com/dpipstudio/botwave/)")
        }

        request = urllib.request.Request(url, headers=headers)

        with urllib.request.urlopen(request) as response, open(dest_path, "wb") as out_file:
            out_file.write(response.read())


def setup(reg):
    reg.register(DownloadUrlOp)