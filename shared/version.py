import urllib.request
import urllib.error
from typing import Optional

from shared.env import Env
from shared.protocol import PROTOCOL_VERSION

# if mismatch of 1st or 2nd part: error
VERSION_CHECK_URL = "https://botwave.dpip.lol/api/latestpro/" # to retrieve the latest ver
RELEASE_FILE = "/opt/BotWave/last_release" # written by install.sh, might not exist on custom installs
RELEASE_CHECK_URL = "https://botwave.dpip.lol/api/latestrel/"

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
                "User-Agent": Env.get("VCHECK_UA", f"BotWaveVCheck/{PROTOCOL_VERSION} (+https://github.com/dpipstudio/botwave/)")
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

def get_release_version() -> Optional[str]:
    # reads the release codename install.sh writes to RELEASE_FILE, like "v1.1.10-mollia"
    # not guaranteed to exist (custom installs, manual setups, deleted file...) and can
    # also be "local:/some/path" for local-repo installs

    try:
        with open(RELEASE_FILE, "r") as f:
            release = f.read().strip()

    except (IOError, OSError):
        return None

    if not release or release.startswith("local:"):
        return None

    return release

def check_for_release_updates() -> Optional[str]:
    # Check for a newer release
    current_release = get_release_version()

    if not current_release:
        # nothing to check, skip
        return None

    try:
        req = urllib.request.Request(
            RELEASE_CHECK_URL,
            headers={
                "User-Agent": Env.get("VCHECK_UA", f"BotWaveVCheck/{PROTOCOL_VERSION} (+https://github.com/dpipstudio/botwave/)")
            }
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            remote_release = response.read().decode('utf-8').strip()

        if remote_release and remote_release != current_release:
            return remote_release
        
        return None
    
    except (urllib.error.URLError, urllib.error.HTTPError, Exception):
        return None