#!/bin/bash

# BotWave - Update script

# A program by Douxx (douxx.tech | github.com/douxxtech)
# https://github.com/douxxtech/botwave
# https://botwave.dpip.lol
# A DPIP Studios project. https://dpip.lol
# Licensed under GPL-v3.0 (see LICENSE)

set -e

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

# ensure we're root
if [[ "$EUID" -ne 0 ]]; then
    log ERROR "This script must be run as root. Try: sudo $0"
    exit 1
fi

INSTALL_DIR="/opt/BotWave"
BIN_DIR="$INSTALL_DIR/bin"
SYMLINK_DIR="/usr/local/bin"

create_symlink() {
    local target="$1"
    local link_name="$2"
    if [[ -e "$SYMLINK_DIR/$link_name" ]]; then
        log WARN "Removing existing symlink or file: $SYMLINK_DIR/$link_name"
        rm -f "$SYMLINK_DIR/$link_name"
    fi
    ln -s "$target" "$SYMLINK_DIR/$link_name"
    log INFO "Symlink created: $SYMLINK_DIR/$link_name -> $target"
}

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
        curl -L https://raw.githubusercontent.com/douxxtech/botwave/main/bin/bw-client -o "$BIN_DIR/bw-client"
        chmod +x "$BIN_DIR/bw-client"
        create_symlink "$BIN_DIR/bw-client" "bw-client"
        log INFO "Client updated."

        log INFO "Updating local client files..."
        mkdir -p local
        curl -L https://raw.githubusercontent.com/douxxtech/botwave/main/local/local.py -o "$INSTALL_DIR/local/client.py"
        curl -L https://raw.githubusercontent.com/douxxtech/botwave/main/bin/bw-local -o "$BIN_DIR/bw-local"
        chmod +x "$BIN_DIR/bw-local"
        create_symlink "$BIN_DIR/bw-local" "bw-local"
        log INFO "Local client updated."

        log INFO "Updating PiWave..."
        ./venv/bin/pip install -U git+https://github.com/douxxtech/piwave.git
        log INFO "PiWave updated."

        log INFO "Updating PiFmRds..."
        rm -rf PiFmRds
        git clone https://github.com/ChristopheJacquet/PiFmRds || true
        cd PiFmRds/src
        make clean
        make
        cd "$INSTALL_DIR"
        log INFO "PiFmRds updated."
    fi

    # update server
    if [[ -d "$INSTALL_DIR/server" ]]; then
        log INFO "Updating server files..."
        curl -L https://raw.githubusercontent.com/douxxtech/botwave/main/server/server.py -o "$INSTALL_DIR/server/server.py"
        curl -L https://raw.githubusercontent.com/douxxtech/botwave/main/bin/bw-server -o "$BIN_DIR/bw-server"
        chmod +x "$BIN_DIR/bw-server"
        create_symlink "$BIN_DIR/bw-server" "bw-server"
        log INFO "Server updated."
    fi

    # update autorun
    log INFO "Updating autorunner..."
    curl -L https://raw.githubusercontent.com/douxxtech/botwave/main/autorun/autorun.py -o "$INSTALL_DIR/autorun/autorun.py"
    curl -L https://raw.githubusercontent.com/douxxtech/botwave/main/bin/bw-autorun -o "$BIN_DIR/bw-autorun"
    chmod +x "$BIN_DIR/bw-autorun"
    create_symlink "$BIN_DIR/bw-autorun" "bw-autorun"
    log INFO "AutoRunner updated."

    # update binaries -> for binaries not related to client/server
    log INFO "Updating general binaries..."
    curl -L https://raw.githubusercontent.com/douxxtech/botwave/main/bin/bw-update -o "$BIN_DIR/bw-update"
    chmod +x "$BIN_DIR/bw-update"
    create_symlink "$BIN_DIR/bw-update" "bw-update"
    log INFO "General binaries updated."

    echo "$LATEST_COMMIT" > "$INSTALL_DIR/last_commit"
    log INFO "Update complete."
else
    log INFO "BotWave is already up-to-date."
fi

cd "$START_PWD"
