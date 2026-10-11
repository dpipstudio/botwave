#!/bin/bash
# shows a ssh-like "last login" page

LAST_LOGIN_FILE="/tmp/botwave/REMOTE_CLIENT_IP"

if [ -f "$LAST_LOGIN_FILE" ]; then
    DATE="$(date -d "@$(stat -c '%Y' "$LAST_LOGIN_FILE")" '+%a %b %d %H:%M:%S %Y')"
    IP="$(cat "$LAST_LOGIN_FILE")"

else
    DATE="$(date '+%a %b %d %H:%M:%S %Y')"
    IP="$(hostname -I)"

fi

echo "Last login on $DATE from $IP"