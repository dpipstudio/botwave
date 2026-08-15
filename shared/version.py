import urllib.request
import urllib.error
from typing import Optional

from shared.dirutils import BW_PATH
from shared.env import Env
from shared.protocol import PROTOCOL_VERSION

# if mismatch of 1st or 2nd part of ver: error
LATEST_CHECK_URL = "https://botwave.dpip.lol/api/latest/" # line 1 = proto, line 2 = release
RELEASE_FILE = f"{BW_PATH}/last_release" # written by install.sh, might not exist on custom installs

def parse_version(version_str: str) -> tuple:
    try:
        return tuple(map(int, version_str.split('.')))
    except (ValueError, AttributeError):
        return (0, 0, 0)

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

def check_for_updates() -> tuple[Optional[str], Optional[str]]:
    # returns (new_proto_version, new_release_version), either can be None
    try:
        req = urllib.request.Request(
            LATEST_CHECK_URL,
            headers={
                "User-Agent": Env.get("VCHECK_UA", f"BotWaveVCheck/{PROTOCOL_VERSION} (+https://github.com/dpipstudio/botwave/)")
            }
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            lines = response.read().decode('utf-8').strip().splitlines()

        remote_proto = lines[0].strip() if len(lines) > 0 else None
        remote_release = lines[1].strip() if len(lines) > 1 else None

        new_proto = None
        current_tuple = parse_version(PROTOCOL_VERSION)
        remote_tuple = parse_version(remote_proto) if remote_proto else (0, 0, 0)

        if remote_proto and remote_tuple > current_tuple:
            new_proto = remote_proto

        new_release = None
        current_release = get_release_version()

        if current_release and remote_release and remote_release != current_release:
            new_release = remote_release

        return (new_proto, new_release)

    except (urllib.error.URLError, urllib.error.HTTPError, Exception):
        # don't interrupt startup for client updates, we do not care
        return (None, None)