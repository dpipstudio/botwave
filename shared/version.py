import urllib.request
import urllib.error
from typing import Optional
from shared.protocol import PROTOCOL_VERSION

# if mismatch of 1th or 2th part: error
VERSION_CHECK_URL = "https://botwave.dpip.lol/api/latestpro/" # to retrieve the lastest ver

def parse_version(version_str: str) -> tuple:
    try:
        return tuple(map(int, version_str.split('.')))
    except (ValueError, AttributeError):
        return (0, 0, 0)

def check_for_updates() -> Optional[str]:
    #Check for protocol updates from remote URL
    try:
        req = urllib.request.Request(
            VERSION_CHECK_URL,
            headers={
                "User-Agent": f"BotWaveVCheck/{PROTOCOL_VERSION}"
            }
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            remote_version = response.read().decode('utf-8').strip()
        
        current_tuple = parse_version(PROTOCOL_VERSION)
        remote_tuple = parse_version(remote_version)
        
        if remote_tuple > current_tuple:
            return remote_version
        return None
    except (urllib.error.URLError, urllib.error.HTTPError, Exception):
        # don't interrupt startup for client updates, we do not care
        return None

def versions_compatible(server_version: str, client_version: str) -> bool:
    server_tuple = parse_version(server_version)
    client_tuple = parse_version(client_version)
    return server_tuple[:2] == client_tuple[:2]