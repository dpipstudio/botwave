#!/bin/bash
# runs bw-update and restarts the component

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(dirname "$SCRIPT_PATH")"

echo '< echo "Updating botwave..."'

# run the update
bw-update > /dev/null 2>&1

echo '< echo "Update successful, restarting soon via systemctl"'

# only kick if on bw-server
if [[ "$COMPONENT" == "server" ]]; then
    echo 'kick all "The server is updating"'
    NAME="server"
else
    NAME="local"
fi

systemctl restart "bw-$NAME" > /dev/null 2>&1