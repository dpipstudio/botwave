from pathlib import Path

from shared.converter import Converter, ConvertError, SUPPORTED_EXTENSIONS
from shared.dirutils import BW_PATH
from shared.env import Env
from shared.logger import Log
from shared.ops import CliOp
from shared.security import PathValidator, SecurityError

class UploadOp(CliOp):
    """
    The 'upload' command OP. Moves a file or the content 
    of a directory to the upload dir. Also converts the files
    to .wav if they're supported.
    """

    name = "upload"
    syntax = "<file|dir>"

    async def handle(self, target: str = None, is_cmd: bool = False, cmd_parts: str = None):
        if is_cmd:
            target = self.parse(cmd_parts)

            if not target:
                return

        allowed_source_dirs = [
            '/tmp',
            '/home',
            BW_PATH,
            Env.get("UPLOAD_DIR"),
            Path.home()
        ]

        try:
            source_path = Path(PathValidator.validate_read(target, allowed_source_dirs))

        except SecurityError as e:
            Log.error(str(e))
            return

        if not source_path.exists():
            Log.error(f"Source {source_path} not found")
            return

        if source_path.is_dir():
            self.upload_folder(source_path)
            return

        self.upload_single(source_path)


    def parse(self, cmd_parts):
        if len(cmd_parts) < 1:
            Log.error("Usage: upload <file|dir>")
            return None

        return cmd_parts[0]

    def upload_folder(self, folder_path):
        upl_dir = Path(Env.get("UPLOAD_DIR"))
        silent = not Env.get_bool("TALK")

        files = [f for f in folder_path.iterdir() if f.is_file()]

        if not files:
            Log.warning(f"No files found in {folder_path}")
            return False

        Log.file(f"Found {len(files)} file(s) in {folder_path}")

        success = 0

        for idx, source_path in enumerate(files, 1):
            filename = source_path.name
            ext = source_path.suffix.lower()

            Log.file(f"[{idx}/{len(files)}] Processing {filename}...")

            try:
                if ext == ".wav":
                    dest_name = PathValidator.sanitize_filename(filename)
                    dest_path = Path(PathValidator.safe_join(upl_dir, dest_name))

                    dest_path.write_bytes(source_path.read_bytes())

                    Log.success(f"  Uploaded {filename}")
                    success += 1

                elif ext.lstrip(".") in SUPPORTED_EXTENSIONS:
                    dest_name = PathValidator.sanitize_filename(source_path.stem + ".wav")
                    dest_path = PathValidator.safe_join(upl_dir, dest_name)

                    Converter.convert_wav(source_path, dest_path, not silent)
                    Log.success(f"  Converted & uploaded {dest_name}")
                    success += 1

                else:
                    Log.warning(f"  Skipped unsupported file: {filename}")

            except (ConvertError, SecurityError, OSError) as e:
                Log.error(f"  {filename} - {e}")

        Log.file(f"Folder upload completed: {success} successful, {len(files) - success} skipped/failed")
        return success > 0

    def upload_single(self, source_path: Path):
        upl_dir = Path(Env.get("UPLOAD_DIR"))
        silent = not Env.get_bool("TALK")

        try:
            filename = source_path.name
            ext = source_path.suffix.lower()

            if ext != ".wav":
                if ext.lstrip(".") not in SUPPORTED_EXTENSIONS:
                    Log.error(f"Unsupported file type: {ext}")
                    return False

                dest_name = PathValidator.sanitize_filename(source_path.stem + ".wav")
                dest_path = PathValidator.safe_join(upl_dir, dest_name)

                Converter.convert_wav(source_path, dest_path, not silent)
                Log.success(f"File converted and uploaded to {dest_path}")
                return True

            dest_name = PathValidator.sanitize_filename(filename)
            dest_path = Path(PathValidator.safe_join(upl_dir, dest_name))

        except SecurityError as e:
            Log.error(f"Invalid destination: {e}")
            return False
        
        except ConvertError as e:
            Log.error(str(e))
            return False

        try:
            dest_path.write_bytes(source_path.read_bytes())
            Log.success(f"File uploaded successfully to {dest_path}")
            return True

        except Exception as e:
            Log.error(f"Error uploading file: {e}")
            return False


def setup(reg):
    reg.register(UploadOp)