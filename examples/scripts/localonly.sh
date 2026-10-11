#!/bin/bash
# when called, checks if the command is run from a remote client
# if so, stops the execution, except if ALLOW_REMOTE_BLOCKED_COMMANDS_I_KNOW_WHAT_IM_DOING
# is set to "true"

if [ -n "$BW_REMOTE_CLIENT_IP" ] &&
   [ "$ALLOW_REMOTE_BLOCKED_COMMANDS_I_KNOW_WHAT_IM_DOING" != "true" ]; then
    echo "< echo {BW_ARGV0} can only be used locally"
    echo "exit"
fi