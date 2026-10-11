#!/bin/bash
# runs bw-update and restarts the component

echo '< echo "Updating botwave..."'

# run the update
if ! bw-update > /dev/null 2>&1; then
    echo '< echo "Update failed, not restarting"'
    exit 1
fi

echo '< echo "Update successful, restarting soon via systemctl"'

# only kick if on bw-server
if [[ "$COMPONENT" == "server" ]]; then
    echo 'kick all "The server is updating"'
    NAME="server"
else
    NAME="local"
fi

systemctl restart "bw-$NAME" > /dev/null 2>&1