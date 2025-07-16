#!/bin/bash

# BotWave - Update script

# A program by Douxx (douxx.tech | github.com/douxxtech)
# https://github.com/douxxtech/botwave
# https://botwave.dpip.lol
# A DPIP Studios project. https://dpip.lol
# Licensed under GPL-v3.0 (see LICENSE)

# ensure we're root
if [[ "$EUID" -ne 0 ]]; then
    log ERROR "This script must be run as root. Try: sudo $0"
    exit 1
fi

START_PWD=$(pwd)


RED='\033[0;31m'
GRN='\033[0;32m'
YEL='\033[1;33m'
NC='\033[0m'

log() {
    local level="$1"
    shift
    local color=""
    case "$level" in
        INFO) color="$GRN" ;;
        WARN) color="$YEL" ;;
        ERROR) color="$RED" ;;
        *) color="$NC" ;;
    esac
    printf "[%s] ${color}%-5s${NC} %s\n" "$(date +%T)" "$level" "$*"
}

INSTALL_DIR="/opt/BotWave_Deps"
cd "$INSTALL_DIR"

log INFO "Checking if we have to update..."

LATEST_COMMIT=$(curl -s https://api.github.com/repos/douxxtech/botwave/commits | grep '"sha":' | head -n 1 | cut -d '"' -f 4)
CURRENT_COMMIT=$(cat "$INSTALL_DIR/last_commit" 2>/dev/null || echo "")

if [[ "$LATEST_COMMIT" != "$CURRENT_COMMIT" ]]; then
    log INFO "New version available. Updating now..."

    # update client
    if [[ -d "$INSTALL_DIR/client" ]]; then
        log INFO "Updating client files..."
        curl -L https://raw.githubusercontent.com/douxxtech/botwave/main/client/client.py -o "$INSTALL_DIR/client/client.py"
        curl -L https://raw.githubusercontent.com/douxxtech/botwave/main/bin/bw-client -o /usr/bin/bw-client
        chmod +x /usr/bin/bw-client
        log INFO "Client updated."

        log INFO "Updating PiWave..."
        ./venv/bin/pip -U git+https://github.com/douxxtech/piwave.git
        log INFO "PiWave updated."

        log INFO "Updating PiFmRds..."
        rm -rf PiFmRds
        git clone https://github.com/ChristopheJacquet/PiFmRds || true
        cd PiFmRds/src
        log INFO "Building PiFmRds..."
        make clean
        make
        cd $INSTALL_DIR
        log INFO "Updated PiFmRds."
    fi

    # update server
    if [[ -d "$INSTALL_DIR/server" ]]; then
        log INFO "Updating server files..."
        curl -L https://raw.githubusercontent.com/douxxtech/botwave/main/server/server.py -o "$INSTALL_DIR/server/server.py"
        curl -L https://raw.githubusercontent.com/douxxtech/botwave/main/bin/bw-server -o /usr/bin/bw-server
        chmod +x /usr/bin/bw-server
        log INFO "Server updated."
    fi

    # update binaries -> for binaries not related to client - server
    log INFO "Updating binaries..."
    curl -L https://raw.githubusercontent.com/douxxtech/botwave/main/bin/bw-update -o /usr/bin/bw-update
    chmod +x /usr/bin/bw-update
    log INFO "Binaries updated."

    echo "$LATEST_COMMIT" > "$INSTALL_DIR/last_commit"
    log INFO "Update complete."
else
    log INFO "BotWave is already up-to-date."
fi

cd $START_PWD