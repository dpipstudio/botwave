from typing import Any

from shared.logger import Log
from shared.ops import CliOp

class ListOp(CliOp):
    """
    The 'list' command OP. Prints information about 
    every connected client.
    """

    name = "list"

    async def handle(self, is_cmd: bool = False, cmd_parts: list[str] = []):
        if not self.owner.clients:
            Log.warning("No clients connected")
            return
        
        Log.section("Connected Clients")
        
        for client_id, client in self.owner.clients.items():
            info = client.machine_info
            
            Log.print(f"ID: {client_id}", 'bright_white')
            Log.print(f"  Hostname: {info.get('hostname', 'unknown')}", 'cyan')
            Log.print(f"  Machine: {info.get('machine', 'unknown')}", 'cyan')
            Log.print(f"  System: {info.get('system', 'unknown')}", 'cyan')
            Log.print(f"  Protocol Version: {client.protocol_version}", 'cyan')
            Log.print(f"  Connected: {client.connected_at.strftime('%Y-%m-%d %H:%M:%S')}", 'cyan')
            Log.print(f"  Last seen: {client.last_seen.strftime('%Y-%m-%d %H:%M:%S')}", 'cyan')
            Log.print("")


def setup(reg: Any):
    reg.register(ListOp)