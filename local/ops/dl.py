from pathlib import Path
import tempfile
import urllib.request

from shared.converter import Converter, ConvertError, SUPPORTED_EXTENSIONS
from shared.env import Env
from shared.logger import Log
from shared.ops import CliOp
from shared.protocol import PROTOCOL_VERSION
from shared.security import PathValidator, SecurityError

class DownloadOp(CliOp):
    name = "dl"
    syntax  = "<url> [destination]"

    async def handle(self, url: str = None, dest_name: str = None, is_cmd: bool = False, cmd_parts: str = []):
        if is_cmd:
            url, dest_name = self.parse(cmd_parts)

            if not url:
                return


        try:
            headers = {
                "User-Agent": Env.get("DOWNLOAD_UA", f"BotWaveDownloads/{PROTOCOL_VERSION} (+https://github.com/dpipstudio/botwave/)")
            }

            if not dest_name:
                url_path = urllib.parse.urlparse(url).path
                dest_name = Path(url_path).name

            dest_name = PathValidator.sanitize_filename(dest_name)
            ext = Path(dest_name).suffix.lower().lstrip(".")

            final_name = str(Path(dest_name).with_suffix(".wav"))

            try:
                final_path = PathValidator.safe_join(Env.get("UPLOAD_DIR"), final_name)

            except SecurityError as e:
                Log.error(f"Invalid destination path: {e}")
                return

            # already wav = download directly
            if ext == "wav":
                Log.file(f"Downloading WAV file from {url}...")
                opener = urllib.request.build_opener()
                opener.addheaders = [(k, v) for k, v in headers.items()]
                urllib.request.install_opener(opener)
                urllib.request.urlretrieve(url, final_path, reporthook=self.reporthook)
                Log.success(f"File {final_name} downloaded successfully to {final_path}")
                return

            # supported but not wav = temp download + convert
            if ext in SUPPORTED_EXTENSIONS:
                Log.file(f"Downloading {ext.upper()} file and converting to WAV...")

                with tempfile.NamedTemporaryFile(delete=False, suffix="." + ext) as tmp:
                    tmp_path = tmp.name

                opener = urllib.request.build_opener()
                opener.addheaders = [(k, v) for k, v in headers.items()]
                urllib.request.install_opener(opener)
                urllib.request.urlretrieve(url, tmp_path, reporthook=self.reporthook)

                Converter.convert_wav(tmp_path, final_path, Env.get_bool("TALK"))

                Path(tmp_path).unlink()

                Log.success(f"File converted and saved to {final_path}")
                return

            Log.error(f"Unsupported file type: .{ext}")
            return

        except (ConvertError, OSError, urllib.error.URLError) as e:
            Log.error(f"Download error: {e}")
            return

    def parse(self, cmd_parts):
        if len(cmd_parts) < 1:
            Log.error("Usage: dl <url> [destination]")
            return (None, None)

        url = cmd_parts[0]
        dest_name = cmd_parts[1] if len(cmd_parts) > 1 else None

        return (url, dest_name)

    def reporthook(self, block_num, block_size, total_size):
        downloaded = block_num * block_size
        if total_size > 0:
            Log.progress_bar(downloaded, total_size, prefix='Downloading:', suffix='Complete', style='yellow', icon='FILE', auto_clear=False )

        if downloaded >= total_size:
            Log.progress_bar(total_size, total_size, prefix='Downloaded!', suffix='Complete', style='yellow', icon='FILE' )


def setup(reg):
    reg.register(DownloadOp)