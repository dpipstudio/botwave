import asyncio
import tempfile
from pathlib import Path
from typing import Any

from shared.converter import Converter, SUPPORTED_EXTENSIONS
from shared.dirutils import BW_PATH
from shared.env import Env
from shared.logger import Log
from shared.ops import CliOp
from shared.protocol import Commands
from shared.security import PathValidator, SecurityError

class UploadOp(CliOp):
    """
    The 'upload' command OP. Uploads a file to the target client
    by generating a download token with the BWHTTPFileServer and
    sending it with Commands.DOWNLOAD_TOKEN. No success tracking
    is currently implemented.

    As for folder uploads, it repeats the file upload step for X
    compatible files in the target folder.
    """

    name = "upload"
    syntax = "<targets> <file|folder>"

    async def handle(
            self,
            targets: list[str] = [],
            file: str = "",
            is_cmd: bool = False,
            cmd_parts: list[str] = []
    ):
        if is_cmd:
            targets, file = self.parse(cmd_parts)

            if not targets:
                return

            targets = self.owner.parse_targets(targets)

            if not targets:
                Log.warning("No client(s) found matching the query")
                return

        extra = Env.get("EXTRA_ALLOWED_DIRS", "")
        extra_dirs = [d for d in extra.split(":") if d.strip()]

        allowed_source_dirs: list[Any] = [
            tempfile.gettempdir(),
            BW_PATH,
            Path.home(),
            *extra_dirs
        ]

        try:
            filepath = PathValidator.validate_read(file, allowed_source_dirs)

        except Exception as e:
            Log.error(str(e))
            return False

        if Path(filepath).is_dir():
            await self.upload_folder(targets, filepath)
            return

        elif Path(filepath).is_file():
            await self.upload_file(targets, filepath)
            return

        else:
            Log.error(f"File does not exist: {filepath}")

    async def upload_file(self, targets: list[str], filepath: str, silent: bool = False):
        try:
            filename = PathValidator.sanitize_filename(Path(filepath).name)

        except SecurityError as e:
            if not silent:
                Log.error(f"Invalid filename: {e}")

            return False

        ext = Path(filename).suffix.lower().lstrip('.')

        if ext != "wav":
            if ext not in SUPPORTED_EXTENSIONS:
                if not silent:
                    Log.error(f"Unsupported file type: .{ext}")
                return False

            tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            tmp.close()

            try:
                Converter.convert_wav(filepath, tmp.name)
                filepath = tmp.name
                filename = str(Path(filename).with_suffix(".wav"))

            except Exception as e:
                try:
                    Path(tmp.name).unlink()

                except Exception:
                    pass

                if not silent:
                    Log.error(f"Conversion failed: {e}")
                return False

        max_size = Env.get_int("MAX_UPLOAD_SIZE", 500 * 1024 * 1024)  # 500 MB
        file_size = Path(filepath).stat().st_size

        if file_size > max_size:
            if not silent:
                Log.error(f"File too large ({file_size} bytes)")
            return False


        results: dict[str, list[str]] = {"failed": [], "uploaded": []}

        for client_id in targets:
            if client_id not in self.owner.clients:
                if not silent:
                    Log.error(f"{client_id}: Client not found")

                results["failed"].append(client_id)
                continue

            token = self.owner.http_server.create_download_token(filepath)
            client = self.owner.clients[client_id]

            await client.proto.fire(
                Commands.DOWNLOAD_TOKEN,
                token=token,
                filename=filename,
                size=file_size
            )
            if not silent:
                Log.success(f"  {client.get_display_name()}: Download requested")

            results["uploaded"].append(client_id)

        if not silent:
            Log.print("")
            Log.info(f"Success: {len(results['uploaded'])}, Failure: {len(results['failed'])}")

        return len(results['uploaded']) >= len(results['failed'])

    async def upload_folder(self, targets: list[str], folder_path: str):
        files = [f.name for f in Path(folder_path).iterdir() if f.is_file()]

        if not files:
            Log.warning(f"No files found in {folder_path}")
            return False

        Log.file(f"Found {len(files)} file(s) in {folder_path}")

        results: dict[str, list[str]] = {"uploaded": [], "failed": []}

        for idx, filename in enumerate(files, 1):
            full_path = Path(folder_path) /  filename

            ext = Path(filename).suffix.lower().lstrip(".")

            if ext == "wav" or ext in SUPPORTED_EXTENSIONS:
                Log.file(f"[{idx}/{len(files)}] Processing {filename}...")

                if await self.upload_file(targets, str(full_path), silent=True):
                    results["uploaded"].append(filename)

                else:
                    results["failed"].append(filename)

            else:
                Log.warning(f"Skipping unsupported file: {filename}")
                results["failed"].append(filename)

            if idx < len(files):
                await asyncio.sleep(0.5)

        Log.print("")
        Log.info(f"Folder upload requests sent!")
        Log.info(f"Success: {len(results['uploaded'])}, Failure: {len(results['failed'])}")

    def parse(self, cmd_parts: list[str]) -> tuple[Any, ...]:
        if len(cmd_parts) < 2:
            Log.error("Usage: upload <targets> <file|folder>")
            return (None, None)

        return (cmd_parts[0], cmd_parts[1])

def setup(reg: Any):
    reg.register(UploadOp)