import asyncio
import json
from pathlib import Path
import tempfile
import uuid

from shared.converter import SUPPORTED_EXTENSIONS
from shared.env import Env
from shared.logger import Log
from shared.ops import CliOp
from shared.protocol import Commands
from shared.security import PathValidator, SecurityError

class SyncOp(CliOp):
    name = "sync"
    syntax = "<targets|folder> <source_target|source_folder>"

    async def handle(
            self,
            target: str = None,
            source: str = None,
            is_cmd: bool = False,
            cmd_parts: list = []
    ):
        if is_cmd:
            target, source = self.parse(cmd_parts)

            if not target:
                return

        Log.info("This feature is experimental and may be unstable")

        is_target_folder = Path(target).is_dir()
        is_source_folder = Path(source).is_dir()

        if is_target_folder and not is_source_folder:
            Log.info(f"Syncing from {source} (client) -> {target} (folder)")
            await self.client_to_local(target, source)

        elif is_source_folder:
            Log.info(f"Syncing from {source} (folder) -> {target} (client(s))")
            await self.local_to_client(target, source)

        elif not is_target_folder and not is_source_folder:
            Log.info(f"Syncing from {source} (client) -> {target} (client(s))")
            await self.client_to_client(target, source)

        else:
            Log.error(f"Unsupported sync operation: {source} -> {target}")
            Log.info("Supported sync operations:")
            Log.info("  - Local folder to client(s)")
            Log.info("  - Client to local folder")
            Log.info("  - Client to client(s)")
    
    async def client_to_local(self, target, source):
        allowed_target_dirs = self.get_allowed_dirs()
        try:
            target = PathValidator.validate_read(target, allowed_target_dirs)

        except SecurityError as e:
            Log.error(str(e))
            return

        source_p = self.owner.parse_targets(source)

        if len(source_p) != 1:
            Log.error(f"Source '{source}' must resolve to exactly one client")
            return

        client = self.owner.clients[source_p[0]]
        Log.info(f"Syncing from {client.get_display_name()} to local folder: {target}")

        files = await self.request_files(client)

        if not files:
            Log.warning(f"{client.get_display_name()} has no files")
            return

        Log.info(f"Found {len(files)} files to sync")

        results = {"downloaded": [], "failed": []}

        for file_info in files:
            filename = file_info.get('name')
            
            try:
                filename = PathValidator.sanitize_filename(filename)

            except SecurityError as e:
                Log.error(f"Invalid filename from client: {e}")
                results["failed"].append(filename)
                continue

            try:
                temp_suffix = uuid.uuid4().hex[:8]
                temp_filename = f".sync_temp_{source}_{temp_suffix}_{filename}"
                
                try:
                    temp_path = PathValidator.safe_join(target, temp_filename)
                    final_path = PathValidator.safe_join(target, filename)

                except SecurityError as e:
                    Log.error(f"Path traversal attempt in sync: {e}")
                    results["failed"].append(filename)
                    continue
                
                token = self.owner.http_server.create_upload_token(
                    temp_filename,
                    0,
                    upload_dir=target
                )
                
                client.proto.execute(
                    Commands.UPLOAD_TOKEN,
                    token=token,
                    filename=filename,
                    size=0
                )
                
                Log.client(f"  [{len(results["downloaded"]) + 1}/{len(files)}] Downloading {filename}...")

                if not await self.wait_for_completion(temp_path):
                    Log.error(f"  {filename} - file never unlocked")
                    continue

                temp_path = Path(temp_path)
                final_path = Path(final_path)
                
                if temp_path.is_file():
                    if final_path.exists():
                        final_path.unlink()

                    temp_path.rename(final_path)
                    
                    file_size = final_path.stat().st_size
                    Log.file(f"  {filename} saved ({file_size} bytes)")
                    results["downloaded"].append(filename)

                else:
                    Log.error(f"  {filename} - timeout")
            
            except Exception as e:
                Log.error(f"  {filename} - {e}")
                try:
                    if temp_path.exists():
                        temp_path.unlink()

                except:
                    pass
        
        if len(results["downloaded"]) > 0:
            Log.print("")
            Log.info(f"Sync completed!")
            Log.info(f"Success: {len(results['downloaded'])}, Failure: {len(results['failed'])}")
        
        else:
            Log.error("Sync failed: no files transferred")

    async def local_to_client(self, target, source):
        allowed_source_dirs = self.get_allowed_dirs()
        try:
            source = PathValidator.validate_read(source, allowed_source_dirs)

        except SecurityError as e:
            Log.error(str(e))
            return
    
        targets = self.owner.parse_targets(target)

        if not targets:
            Log.warning("No client(s) found matching the query")
            return

        supported_files = [
            f.name for f in Path(source).iterdir()
            if f.is_file() and 
            (f.suffix.lower() == '.wav' or f.suffix.lower().lstrip('.') in SUPPORTED_EXTENSIONS)
        ]

        if not supported_files:
            Log.warning(f"No supported files found in {source}")
            return False

        Log.info(f"Syncing from local folder: {source} ({len(supported_files)} files)")
        Log.info(f"Targets: {', '.join(targets)}")

        Log.info("Clearing existing files on targets...")
        await self.registry.dispatch("rm", targets=targets, file="*.wav")
        await asyncio.sleep(1)

        await self.registry.dispatch(
            "upload",
            targets=targets,
            file=source
        )

    async def client_to_client(self, target, source):
        target_p = self.owner.parse_targets(target)
        source_p = self.owner.parse_targets(source)

        if len(source_p) != 1:
            Log.error(f"Source '{source}' must resolve to exactly one client")
            return

        if source_p in target_p and len(target_p) == 1:
            Log.error("Source and target is the same client")
            return

        tmp_dir = tempfile.mkdtemp(prefix="bw_sync")

        await self.client_to_local(tmp_dir, source)
        await self.local_to_client(target, tmp_dir)

        #TODO: check how to delete the tempdir when we're sure that all the clients downloaded all the files :/

    async def request_files(self, client, timeout: int = 30):        
        try:
            response = await client.proto.send(Commands.LIST_FILES, timeout=float(timeout))
            return json.loads(response['kwargs'].get('files', '[]'))
        
        except Exception as e:
            Log.error(f"Error getting file list: {e}")
            return None      

    def get_allowed_dirs(self):
        extra = Env.get("EXTRA_ALLOWED_DIRS", "")
        extra_dirs = [d for d in extra.split(":") if d.strip()]

        allowed_dirs = [
            tempfile.gettempdir(),
            "/opt/BotWave",
            Path.home(),
            *extra_dirs
        ]

        return allowed_dirs

    async def wait_for_completion(self, path, timeout=120):
        last_size = -1
        stable_cycles = 0
        elapsed = 0

        path = Path(path)

        while elapsed < timeout:
            if path.is_file():
                try:
                    size = path.stat().st_size

                    with open(path, "rb"):
                        pass

                    if size == last_size:
                        stable_cycles += 1
                    else:
                        stable_cycles = 0
                        last_size = size

                    if stable_cycles >= 3:
                        return True

                except:
                    pass

            await asyncio.sleep(0.5)
            elapsed += 0.5

        return False  

    def parse(self, cmd_parts):
        if len(cmd_parts) < 2:
            Log.error("Usage: sync <targets|folder> <source_target|source_folder>")
            return (None, None)

        return (cmd_parts[0], cmd_parts[1])


def setup(reg):
    reg.register(SyncOp)