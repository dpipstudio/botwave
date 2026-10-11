#!/bin/bash

# install.sh: installs bw_examples into BotWave.
# Run as root: sudo bash install.sh

PLUGIN_NAME="bw_examples"
BW_INSTALL="/opt/BotWave"

if [ "$EUID" -ne 0 ]; then
    echo "Error: run as root (sudo bash install.sh)"
    exit 1
fi

if [ ! -d "$BW_INSTALL" ]; then
    echo "Error: BotWave not found at $BW_INSTALL"
    exit 1
fi

mkdir -p "$BW_INSTALL/scripts/$PLUGIN_NAME"
cp scripts/* "$BW_INSTALL/scripts/$PLUGIN_NAME/"
chmod +x "$BW_INSTALL/scripts/$PLUGIN_NAME/"*.sh

cp handlers/* "$BW_INSTALL/handlers/"

echo "$PLUGIN_NAME installed."