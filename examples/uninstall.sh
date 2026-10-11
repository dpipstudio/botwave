#!/bin/bash

# uninstall.sh: removes bw_examples from BotWave.
# Run as root: sudo bash uninstall.sh

PLUGIN_NAME="bw_examples"
BW_INSTALL="/opt/BotWave"

if [ "$EUID" -ne 0 ]; then
    echo "Error: run as root (sudo bash uninstall.sh)"
    exit 1
fi

# Remove scripts
rm -rf "$BW_INSTALL/scripts/$PLUGIN_NAME"

# Remove handlers (only the ones we installed)
for f in handlers/*; do
    rm -f "$BW_INSTALL/handlers/$(basename $f)"
done

echo "$PLUGIN_NAME uninstalled."