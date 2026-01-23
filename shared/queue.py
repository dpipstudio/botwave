from .logger import Log
import os
from typing import List, Dict, Set, Optional
import asyncio
import fnmatch

class Queue:
    def __init__(self, server_instance=None, client_instance=None, is_local=False, upload_dir="/opt/BotWave/uploads"):
        self.queue = []
        self.server = server_instance
        self.client = client_instance
        self.is_local = is_local
        self.upload_dir = upload_dir
        self.paused = True
        self.current_index = 0
        self.client_indices = {}  # {client_id: current_index}
        self.active_targets = "all"  # remember which targets we're playing on

    def parse(self, command: str):
        if not command:
            self.show("")
            return
            
        first = command[0]
        
        if first == "+":
            action = self.add
        elif first == "-":
            action = self.remove
        elif first == "*":
            action = self.show
        elif first == "?":
            action = self.help
        elif first == "!":
            action = self.toggle
        else:
            Log.error(f"Invalid Actions: {first}.")
            Log.queue(f"Use 'queue ?' for help.")
            return
        
        command = command[1:].strip()
        action(command)

    def add(self, command: str):
        """Add files to queue. Supports: file, file1,file2, pattern_*, or *"""
        force = command.endswith("!")
        if force:
            command = command[:-1].strip()
        
        if not command:
            Log.error("No file specified")
            return
        
        file_specs = [f.strip() for f in command.split(',')]
        
        if self.is_local:
            self._add_local(file_specs, force)
        else:
            asyncio.create_task(self._add_server(file_specs, force))

    def _add_local(self, file_specs: List[str], force: bool):
        """Add files locally"""
        added = []
        for spec in file_specs:
            if '*' in spec:
                files = self._match_files_local(spec, self.upload_dir)
                added.extend(files)
            else:
                if os.path.exists(os.path.join(self.upload_dir, spec)):
                    added.append(spec)
                else:
                    Log.warning(f"File not found: {spec}")
        
        self.queue.extend(added)
        Log.queue(f"Added {len(added)} file(s) to queue")
        
        self.show("")

    async def _add_server(self, file_specs: List[str], force: bool):
        """Add files on server & checks all clients have them (unless forced)"""
        if not self.server or not self.server.clients:
            Log.error("No clients connected")
            return
        
        # if forcing, just add the specs directly without checking clients
        if force:
            added = []
            for spec in file_specs:
                if '*' in spec:
                    # Get from first client
                    client_ids = list(self.server.clients.keys())
                    if client_ids:
                        client_files = await self._get_all_client_files([client_ids[0]])
                        if client_files:
                            all_files = list(client_files.values())[0]
                            if spec == '*':
                                added.extend(sorted(all_files))
                            else:
                                pattern_matches = [f for f in all_files if fnmatch.fnmatch(f, spec)]
                                added.extend(sorted(pattern_matches))
                else:
                    added.append(spec)
            
            self.queue.extend(added)
            Log.queue(f"Added {len(added)} file(s) to queue (forced)")
            self.show("")
            return
        
        client_ids = list(self.server.clients.keys())
        
        client_files = await self._get_all_client_files(client_ids)
        
        if not client_files:
            Log.error("Could not retrieve file lists from clients")
            return
        
        candidates, missing_per_client = self._resolve_file_specs(file_specs, client_files)
        
        if not candidates:
            Log.error("No matching files found on all clients.")
            Log.queue("Use '!' at the end to force add anyway (e.g., 'queue +file!')")
            return
        
        # check if any files are missing on some clients
        if missing_per_client:
            Log.error("Some files are not present on all clients:")
            for client_id, missing_files in missing_per_client.items():
                if missing_files:
                    client_name = self.server.clients[client_id].get_display_name()
                    Log.error(f"  {client_name}: missing {', '.join(list(missing_files)[:3])}{'...' if len(missing_files) > 3 else ''}")
            Log.queue("Use '!' at the end to force add anyway (e.g., 'queue +file!')")
            return
        
        self.queue.extend(candidates)
        Log.queue(f"Added {len(candidates)} file(s) to queue")
        self.show("")

    async def _get_all_client_files(self, client_ids: List[str]) -> Dict[str, Set[str]]:
        """Get file lists from all clients"""
        client_files = {}
        
        for client_id in client_ids:
            try:
                files = await self.server._request_file_list(client_id, timeout=10)
                if files:
                    client_files[client_id] = set(f['name'] for f in files)
                else:
                    Log.warning(f"No files from {client_id}")
                    client_files[client_id] = set()
            except Exception as e:
                Log.error(f"Error getting files from {client_id}: {e}")
                client_files[client_id] = set()
        
        return client_files

    def _resolve_file_specs(self, file_specs: List[str], client_files: Dict[str, Set[str]]) -> tuple[List[str], Dict[str, Set[str]]]:
        """Resolve file specs to actual files that exist on ALL clients
        Returns: (common_files, missing_per_client)
        """
        if not client_files:
            return [], {}
        
        non_empty_client_files = [files for files in client_files.values() if files]
        
        if not non_empty_client_files:
            return [], {}
        
        # find intersection of all client files (only non-empty ones)
        common_files = set.intersection(*non_empty_client_files)
        
        matched = set()
        requested_files = set()
        
        for spec in file_specs:
            if spec == '*':
                # All common files
                matched.update(common_files)
                # For *, we consider all files from any client as "requested"
                for files in client_files.values():
                    requested_files.update(files)
            elif '*' in spec:
                # Wildcard pattern - check against common files
                pattern_matches = [f for f in common_files if fnmatch.fnmatch(f, spec)]
                matched.update(pattern_matches)
                
                # Also find all files that match the pattern on any client
                for files in client_files.values():
                    requested_files.update([f for f in files if fnmatch.fnmatch(f, spec)])
                
                if not pattern_matches:
                    Log.warning(f"No files match pattern on all clients: {spec}")
            else:
                # Exact file
                requested_files.add(spec)
                if spec in common_files:
                    matched.add(spec)
        
        # Calculate which files are missing on which clients
        missing_per_client = {}
        if requested_files:
            for client_id, files in client_files.items():
                missing = requested_files - files
                if missing:
                    missing_per_client[client_id] = missing
        
        return sorted(list(matched)), missing_per_client

    def _match_files_local(self, pattern: str, directory: str) -> List[str]:
        """Match files using wildcard pattern"""
        try:
            all_files = [f for f in os.listdir(directory) if f.endswith('.wav')]
            if pattern == '*':
                return sorted(all_files)
            return sorted([f for f in all_files if fnmatch.fnmatch(f, pattern)])
        except Exception as e:
            Log.error(f"Error matching files: {e}")
            return []

    def remove(self, command: str):
        """Remove files from queue. Same syntax as add"""
        if not command:
            Log.error("No file specified")
            return
        
        file_specs = [f.strip() for f in command.split(',')]
        
        removed_count = 0
        for spec in file_specs:
            if spec == '*':
                # Remove all
                removed_count = len(self.queue)
                self.queue = []
                break
            elif '*' in spec:
                # Wildcard removal
                original_len = len(self.queue)
                self.queue = [f for f in self.queue if not fnmatch.fnmatch(f, spec)]
                removed_count += original_len - len(self.queue)
            else:
                # Exact file
                if spec in self.queue:
                    self.queue.remove(spec)
                    removed_count += 1
        
        Log.queue(f"Removed {removed_count} file(s) from queue")
        self.show("")

    def show(self, command: str = ""):
        """Display current queue"""
        if not self.queue:
            Log.queue("Queue is empty")
            return
        
        status = "PAUSED" if self.paused else "PLAYING"
        
        if self.is_local:
            Log.queue(f"Queue ({len(self.queue)} files) - {status}:")
            for i, filename in enumerate(self.queue, 1):
                marker = "> " if i == self.current_index + 1 else "  "
                Log.print(f"{marker}{i}. {filename}", 'cyan')
        else:
            # Show per-client progress
            Log.queue(f"Queue ({len(self.queue)} files) - {status}:")
            
            if self.client_indices:
                Log.print("Client positions:", 'yellow')
                for client_id, index in self.client_indices.items():
                    if client_id in self.server.clients:
                        client_name = self.server.clients[client_id].get_display_name()
                        current_file = self.queue[index] if index < len(self.queue) else "finished"
                        Log.print(f"  {client_name}: [{index + 1}/{len(self.queue)}] {current_file}", 'cyan')
            
            Log.print("\nQueue:", 'yellow')
            for i, filename in enumerate(self.queue, 1):
                Log.print(f"  {i}. {filename}", 'white')

    def help(self, command: str):
        """Show help"""
        Log.queue("Queue Commands:")
        Log.print("  queue +file            - Add file to queue", 'white')
        Log.print("  queue +file1,file2     - Add multiple files", 'white')
        Log.print("  queue +pattern_*       - Add files matching pattern", 'white')
        Log.print("  queue +*               - Add all files", 'white')
        Log.print("  queue +file!           - Force add (even if not on all clients)", 'white')
        Log.print("  queue -file            - Remove file from queue", 'white')
        Log.print("  queue -*               - Clear queue", 'white')
        Log.print("  queue *                - Show queue", 'white')
        Log.print("  queue !                - Toggle play/pause (local or all)", 'white')
        Log.print("  queue !targets         - Toggle play/pause on specific targets", 'white')

    def toggle(self, command: str):
        """Toggle between play/pause - queue !<targets>"""
        if self.is_local:
            self._toggle_local()
        else:
            targets = command.strip() if command.strip() else "all"
            asyncio.create_task(self._toggle_server(targets))

    def _toggle_local(self):
        """Toggle queue playback locally"""
        if not self.queue:
            Log.error("Queue is empty")
            return
        
        self.paused = not self.paused
        status = "paused" if self.paused else "playing"
        Log.queue(f"Queue {status}")
        
        if not self.paused:
            # Start playing current file
            self._play_current_local()

    def _play_current_local(self):
        """Play current file in queue (local client only)"""
        if self.current_index >= len(self.queue):
            Log.queue("End of queue reached")
            self.paused = True
            self.current_index = 0
            return
        
        if not self.client:
            Log.error("No client instance available")
            return
        
        filename = self.queue[self.current_index]
        file_path = os.path.join(self.upload_dir, filename)
        
        Log.queue(f"Playing [{self.current_index + 1}/{len(self.queue)}]: {filename}")
        
        if os.path.exists(file_path):
            # Call client's start_broadcast
            self.client.start_broadcast(file_path, frequency=90.0, loop=False)
        else:
            Log.error(f"File not found: {filename}")
            self._next_local()

    async def _toggle_server(self, targets: str):
        """Toggle queue playback on server"""
        if not self.queue:
            Log.error("Queue is empty")
            return
        
        if not self.server:
            Log.error("No server instance")
            return
        
        self.paused = not self.paused
        status = "paused" if self.paused else "playing"
        self.active_targets = targets
        Log.queue(f"Queue {status} on {targets}")
        
        if not self.paused:
            # Initialize client indices for the targets
            target_clients = self.server._parse_client_targets(targets)
            for client_id in target_clients:
                if client_id not in self.client_indices:
                    self.client_indices[client_id] = 0
            
            # Start playing from each client's current position
            await self._play_all_clients(target_clients)
        else:
            # Stop current broadcast on targets
            await self.server.stop_broadcast(targets)

    async def _play_all_clients(self, target_clients: List[str]):
        """Start playback for all target clients at their individual positions"""
        for client_id in target_clients:
            index = self.client_indices.get(client_id, 0)
            
            if index >= len(self.queue):
                Log.queue(f"{self.server.clients[client_id].get_display_name()}: Queue finished")
                continue
            
            filename = self.queue[index]
            client_name = self.server.clients[client_id].get_display_name()
            
            Log.queue(f"{client_name}: Playing [{index + 1}/{len(self.queue)}] {filename}")
            
            # Start broadcast on this specific client
            await self.server.start_broadcast(client_id, filename, frequency=90.0, loop=False)

    def on_broadcast_ended(self, client_id: str = None):
        """Called when a broadcast ends - advance to next in queue"""
        if self.paused:
            return
        
        if self.is_local:
            self._next_local()
        else:
            asyncio.create_task(self._next_server(client_id))

    def _next_local(self):
        """Move to next file in queue (local)"""
        self.current_index += 1
        
        if self.current_index >= len(self.queue):
            Log.queue("Queue finished")
            self.current_index = 0
            self.paused = True
            return
        
        self._play_current_local()

    async def _next_server(self, client_id: str):
        """Move to next file in queue for specific client (server)"""
        if not client_id or client_id not in self.client_indices:
            Log.warning(f"Client {client_id} not in queue tracking")
            return
        
        # Increment this client's index
        self.client_indices[client_id] += 1
        client_index = self.client_indices[client_id]
        
        if client_index >= len(self.queue):
            client_name = self.server.clients[client_id].get_display_name()
            Log.queue(f"{client_name}: Queue finished")
            return
        
        # Play next file for this specific client
        filename = self.queue[client_index]
        client_name = self.server.clients[client_id].get_display_name()
        
        Log.queue(f"{client_name}: Next [{client_index + 1}/{len(self.queue)}] {filename}")
        
        # Start broadcast on this specific client only
        await self.server.start_broadcast(client_id, filename, frequency=90.0, loop=False)