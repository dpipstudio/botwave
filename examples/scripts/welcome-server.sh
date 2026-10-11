#!/bin/bash

PORT=$(echo "$PORT" | sed 's/^immutable(\(.*\))$/\1/')

echo "+------------------------------------------------------------+"
echo "|                                                            |"
echo "|               Welcome to the BotWave Server!               |"
echo "|                                                            |"
echo "+------------------------------------------------------------+"

bash /opt/BotWave/scripts/bw_examples/lastlogin.sh

echo "Connect clients with 'sudo bw-client $(hostname -I) --port $PORT'"