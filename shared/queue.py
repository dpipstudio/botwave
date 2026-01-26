from .logger import Log
import os
from typing import List, Dict, Set
import asyncio
import fnmatch


class Queue:
    """Queue system for managing and playing broadcast files in sequence.
    
    Supports both local (single client) and server (multi-client) modes.
    """
    
    def __init__(self, server_instance=None, client_instance=None, is_local=False, upload_dir="/opt/BotWave/uploads"):
        """Initialize the queue system.
        
        Args:
            server_instance: BotWaveServer instance (for server mode)
            client_instance: BotWaveCLI instance (for local mode)
            is_local: True for local client mode, False for server mode
            upload_dir: Directory containing broadcast files
        """
        # Queue data
        self.queue = []
        self.paused = True
        self.current_index = 0  # For local mode
        self.client_indices = {}  # {client_id: current_index} for server mode
        
        # Instances
        self.server = server_instance
        self.client = client_instance
        self.is_local = is_local
        self.upload_dir = upload_dir
        
        # Playback settings
        self.active_targets = "all"
        self.broadcast_settings = {
            'frequency': 90.0,
            'loop': False,
            'ps': 'BotWave',
            'rt': 'Broadcasting',
            'pi': 'FFFF'
        }
    
    # COMMAND PARSER
    
    def parse(self, command: str):
        """Parse and execute queue commands.
        
        Commands:
            + : Add files to queue
            - : Remove files from queue
            * : Show queue
            ? : Show help
            ! : Toggle play/pause
        """
        if not command:
            self.show("")
            Log.queue("Use 'queue ?' for help.")
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
            Log.error(f"Invalid action: {first}")
            Log.queue("Use 'queue ?' for help")
            return
        
        command = command[1:].strip()
        action(command)


    # MANUAL QUEUE PAUSE

    def manual_pause(self):
        """
        Pauses the queue if it is playing.
        To be used on manual 'start', 'live', etc. commands.
        """

        if not self.paused:
            Log.queue("Auto-pausing queue due to manual action")
            self.paused = True
    
    # ADD FILES TO QUEUE
    
    def add(self, command: str):
        """Add files to queue.
        
        Supports:
            - Single file: file.wav
            - Multiple files: file1.wav,file2.wav
            - Wildcard patterns: pattern_*.wav or *
            - Force add: file.wav! (skip availability checks in server mode)
        """
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
        """Add files in local mode."""
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
        """Add files in server mode with client availability checks."""
        if not self.server or not self.server.clients:
            Log.error("No clients connected")
            return
        
        # Force mode: add without checking all clients
        if force:
            added = []
            for spec in file_specs:
                if '*' in spec:
                    # Get files from first available client
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
        
        # Normal mode: check all clients have the files
        client_ids = list(self.server.clients.keys())
        client_files = await self._get_all_client_files(client_ids)
        
        if not client_files:
            Log.error("Could not retrieve file lists from clients")
            return
        
        candidates, missing_per_client = self._resolve_file_specs(file_specs, client_files)
        
        if not candidates:
            Log.error("No matching files found on all clients")
            Log.queue("Use '!' at the end to force add anyway (e.g., 'queue +file!')")
            return
        
        # Check for missing files
        if missing_per_client:
            Log.error("Some files are not present on all clients:")
            for client_id, missing_files in missing_per_client.items():
                if missing_files:
                    client_name = self.server.clients[client_id].get_display_name()
                    missing_list = ', '.join(list(missing_files)[:3])
                    suffix = '...' if len(missing_files) > 3 else ''
                    Log.error(f"  {client_name}: missing {missing_list}{suffix}")
            Log.queue("Use '!' at the end to force add anyway (e.g., 'queue +file!')")
            return
        
        self.queue.extend(candidates)
        Log.queue(f"Added {len(candidates)} file(s) to queue")
        self.show("")
    
    async def _get_all_client_files(self, client_ids: List[str]) -> Dict[str, Set[str]]:
        """Retrieve file lists from all specified clients."""
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
        """Resolve file specs to actual files that exist on ALL clients.
        
        Returns:
            (common_files, missing_per_client)
        """
        if not client_files:
            return [], {}
        
        non_empty_client_files = [files for files in client_files.values() if files]
        
        if not non_empty_client_files:
            return [], {}
        
        # Find intersection of all client files
        common_files = set.intersection(*non_empty_client_files)
        
        matched = set()
        requested_files = set()
        
        for spec in file_specs:
            if spec == '*':
                # All common files
                matched.update(common_files)
                # For *, consider all files from any client as "requested"
                for files in client_files.values():
                    requested_files.update(files)
            elif '*' in spec:
                # Wildcard pattern
                pattern_matches = [f for f in common_files if fnmatch.fnmatch(f, spec)]
                matched.update(pattern_matches)
                
                # Find all files matching pattern on any client
                for files in client_files.values():
                    requested_files.update([f for f in files if fnmatch.fnmatch(f, spec)])
                
                if not pattern_matches:
                    Log.warning(f"No files match pattern on all clients: {spec}")
            else:
                # Exact file
                requested_files.add(spec)
                if spec in common_files:
                    matched.add(spec)
        
        # Calculate missing files per client
        missing_per_client = {}
        if requested_files:
            for client_id, files in client_files.items():
                missing = requested_files - files
                if missing:
                    missing_per_client[client_id] = missing
        
        return sorted(list(matched)), missing_per_client
    
    def _match_files_local(self, pattern: str, directory: str) -> List[str]:
        """Match files using wildcard pattern in local directory."""
        try:
            all_files = [f for f in os.listdir(directory) if f.endswith('.wav')]
            if pattern == '*':
                return sorted(all_files)
            return sorted([f for f in all_files if fnmatch.fnmatch(f, pattern)])
        except Exception as e:
            Log.error(f"Error matching files: {e}")
            return []
    
    # REMOVE FILES FROM QUEUE
    
    def remove(self, command: str):
        """Remove files from queue.
        
        Supports same syntax as add:
            - Single file: file.wav
            - Multiple files: file1.wav,file2.wav
            - Wildcard patterns: pattern_*.wav
            - Clear all: *
        """
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
    
    # SHOW QUEUE
    
    def show(self, command: str = ""):
        """Display current queue status."""
        if not self.queue:
            Log.queue("Queue is empty")
            return
        
        status = "PAUSED" if self.paused else "PLAYING"
        
        if self.is_local:
            # Local mode: show simple list with current position
            Log.queue(f"Queue ({len(self.queue)} files) - {status}:")
            for i, filename in enumerate(self.queue, 1):
                marker = "> " if i == self.current_index + 1 else "  "
                Log.print(f"{marker}{i}. {filename}", 'cyan')
        else:
            # Server mode: show per-client progress
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
    
    # HELP
    
    def help(self, command: str):
        """Display queue command help."""
        Log.queue("Queue Commands:")
        Log.print("  queue +file                - Add file to queue", 'white')
        Log.print("  queue +file1,file2         - Add multiple files", 'white')
        Log.print("  queue +pattern_*           - Add files matching pattern", 'white')
        Log.print("  queue +*                   - Add all files", 'white')
        Log.print("  queue +file!               - Force add (skip availability checks)", 'white')
        Log.print("  queue -file                - Remove file from queue", 'white')
        Log.print("  queue -*                   - Clear queue", 'white')
        Log.print("  queue *                    - Show queue", 'white')
        Log.print("  queue !                    - Toggle play/pause with defaults", 'white')

        if not self.is_local:
            Log.print("  queue !targets             - Toggle on specific targets", 'white')
            Log.print("  queue !targets,freq,loop,ps,rt,pi - Toggle with custom settings", 'white')
            Log.print('    Example: queue !all,100.5,false,"My Radio","Live",ABCD', 'white')
        else:
            Log.print("  queue !freq,loop,ps,rt,pi - Toggle with custom settings", 'white')
            Log.print('    Example: queue !100.5,false"My Radio","Live",ABCD', 'white')
    
    # TOGGLE PLAY/PAUSE
    
    def toggle(self, command: str):
        """Toggle between play and pause states.
        
        Supports custom broadcast parameters:
            Server: queue !targets,freq,ps,rt,pi
            Local:  queue !freq,ps,rt,pi
        
        Examples:
            queue !                                        # Defaults
            queue !all,100.5                               # Custom frequency
            queue !all,90.0,false,"My Radio","Live",ABCD   # Full custom settings
        """
        args = self._parse_toggle_args(command)
        
        if self.is_local:
            self._toggle_local(args)
        else:
            asyncio.create_task(self._toggle_server(args))
    
    def _parse_toggle_args(self, command: str) -> dict:
        """Parse toggle command arguments with support for quoted strings.
        
        Server format: targets,freq,loop,ps,rt,pi
        Local format:  freq,loop,ps,rt,pi
        """
        defaults = {
            'targets': 'all',
            'frequency': 90.0,
            'loop': False,
            'ps': 'BotWave',
            'rt': 'Broadcasting',
            'pi': 'FFFF'
        }

        if not command.strip():
            return defaults

        def parse_bool(value: str) -> bool:
            return value.lower() == 'true'

        try:
            parts = []
            current = []
            in_quotes = False
            quote_char = None

            for char in command:
                if char in ('"', "'") and not in_quotes:
                    in_quotes = True
                    quote_char = char
                elif char == quote_char and in_quotes:
                    in_quotes = False
                    quote_char = None
                elif char == ',' and not in_quotes:
                    parts.append(''.join(current).strip())
                    current = []
                    continue

                current.append(char)

            if current:
                parts.append(''.join(current).strip())

            parts = [p.strip('"').strip("'") for p in parts]

            if not self.is_local:
                # Server: targets,freq,loop,ps,rt,pi
                if len(parts) > 0 and parts[0]:
                    defaults['targets'] = parts[0]
                if len(parts) > 1 and parts[1]:
                    defaults['frequency'] = float(parts[1])
                if len(parts) > 2 and parts[2]:
                    defaults['loop'] = parse_bool(parts[2])
                if len(parts) > 3 and parts[3]:
                    defaults['ps'] = parts[3]
                if len(parts) > 4 and parts[4]:
                    defaults['rt'] = parts[4]
                if len(parts) > 5 and parts[5]:
                    defaults['pi'] = parts[5]
            else:
                # Local: freq,loop,ps,rt,pi
                if len(parts) > 0 and parts[0]:
                    defaults['frequency'] = float(parts[0])
                if len(parts) > 1 and parts[1]:
                    defaults['loop'] = parse_bool(parts[1])
                if len(parts) > 2 and parts[2]:
                    defaults['ps'] = parts[2]
                if len(parts) > 3 and parts[3]:
                    defaults['rt'] = parts[3]
                if len(parts) > 4 and parts[4]:
                    defaults['pi'] = parts[4]

            return defaults

        except Exception as e:
            Log.error(f"Error parsing toggle args: {e}")
            return defaults

    
    def _toggle_local(self, args: dict):
        """Toggle queue playback in local mode."""
        if not self.queue:
            Log.error("Queue is empty")
            return
        
        self.paused = not self.paused
        status = "paused" if self.paused else "playing"
        Log.queue(f"Queue {status}")
        
        if not self.paused:
            self.broadcast_settings = args
            self._play_current_local()
    
    async def _toggle_server(self, args: dict):
        """Toggle queue playback in server mode."""
        if not self.queue:
            Log.error("Queue is empty")
            return
        
        if not self.server:
            Log.error("No server instance")
            return
        
        self.paused = not self.paused
        status = "paused" if self.paused else "playing"
        self.active_targets = args['targets']
        self.broadcast_settings = args
        
        Log.queue(f"Queue {status} on {args['targets']}")
        
        if not self.paused:
            # Initialize client indices for targets
            target_clients = self.server._parse_client_targets(args['targets'])
            for client_id in target_clients:
                if client_id not in self.client_indices:
                    self.client_indices[client_id] = 0
            
            await self._play_all_clients(target_clients)
        else:
            # Stop broadcast on targets
            await self.server.stop_broadcast(args['targets'])
    
    # PLAYBACK CONTROL
    
    def _play_current_local(self):
        """Play current file in local mode."""
        if self.current_index >= len(self.queue):
            Log.queue(f"End of queue reached")
            self.paused = True
            self.current_index = 0
            return
        
        if not self.client:
            Log.error("No client instance available")
            return
        
        filename = self.queue[self.current_index]
        file_path = os.path.join(self.upload_dir, filename)
        
        if not os.path.exists(file_path):
            Log.error(f"File not found: {filename}")
            self._next_local()
            return
        
        Log.queue(f"Playing [{self.current_index + 1}/{len(self.queue)}]: {filename}")
        
        # Use stored broadcast settings
        self.client.start_broadcast(
            file_path,
            frequency=self.broadcast_settings['frequency'],
            ps=self.broadcast_settings['ps'],
            rt=self.broadcast_settings['rt'],
            pi=self.broadcast_settings['pi'],
            loop=False,
            trigger_manual=False
        )
    
    async def _play_all_clients(self, target_clients: List[str]):
        """Start playback for all target clients at their individual positions."""
        for client_id in target_clients:
            index = self.client_indices.get(client_id, 0)
            
            if index >= len(self.queue):
                Log.queue(f"{self.server.clients[client_id].get_display_name()}: Queue finished")
                continue
            
            filename = self.queue[index]
            client_name = self.server.clients[client_id].get_display_name()
            
            Log.queue(f"{client_name}: Playing [{index + 1}/{len(self.queue)}] {filename}")
            
            # Use stored broadcast settings
            await self.server.start_broadcast(
                client_id,
                filename,
                frequency=self.broadcast_settings['frequency'],
                ps=self.broadcast_settings['ps'],
                rt=self.broadcast_settings['rt'],
                pi=self.broadcast_settings['pi'],
                loop=False,
                trigger_manual=False
            )
    
    # AUTO-ADVANCE (NEXT TRACK)
    
    def on_broadcast_ended(self, client_id: str = None):
        """Called when a broadcast ends - advance to next in queue.
        
        Args:
            client_id: Client that finished (server mode only)
        """
        if self.paused:
            return
        
        if self.is_local:
            self._next_local()
        else:
            asyncio.create_task(self._next_server(client_id))
    
    def _next_local(self):
        """Advance to next file in local mode."""
        self.current_index += 1
        
        if self.current_index >= len(self.queue):
            startagain = ", starting over" if self.broadcast_settings['loop'] else ""
            Log.queue(f"Queue finished{startagain}")
            self.current_index = 0
            if not startagain:
                self.paused = True
                return
        
        self._play_current_local()
    
    async def _next_server(self, client_id: str):
        """Advance to next file for specific client in server mode."""
        if not client_id or client_id not in self.client_indices:
            Log.warning(f"Client {client_id} not in queue tracking")
            return
        
        # Increment this client's index
        self.client_indices[client_id] += 1
        client_index = self.client_indices[client_id]
        
        if client_index >= len(self.queue):
            client_name = self.server.clients[client_id].get_display_name()
            startagain = ", starting over" if self.broadcast_settings['loop'] else ""
            Log.queue(f"{client_name}: Queue finished{startagain}")
            self.client_indices[client_id] = 0
            client_index = 0

            if not startagain:
                return
        
        # Play next file for this client
        filename = self.queue[client_index]
        client_name = self.server.clients[client_id].get_display_name()
        
        Log.queue(f"{client_name}: Next [{client_index + 1}/{len(self.queue)}] {filename}")
        
        # Use stored broadcast settings
        await self.server.start_broadcast(
            client_id,
            filename,
            frequency=self.broadcast_settings['frequency'],
            ps=self.broadcast_settings['ps'],
            rt=self.broadcast_settings['rt'],
            pi=self.broadcast_settings['pi'],
            loop=False,
            trigger_manual=False
        )