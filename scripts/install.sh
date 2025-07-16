#!/bin/bash

# BotWave - Install script

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

# validate input
if [[ "$1" != "client" && "$1" != "server" && "$1" != "both" ]]; then
    log ERROR "Usage: $0 {client|server|both}"
    exit 1
fi
MODE="$1"
log INFO "Mode selected: $MODE"

# ensure we're root
if [[ "$EUID" -ne 0 ]]; then
    log ERROR "This script must be run as root. Try: sudo $0 $1"
    exit 1
fi

# check OS
if [[ "$(uname)" != "Linux" && "$(uname)" != "Darwin" ]]; then
    log ERROR "This script must be run on a Unix-like system (Linux/macOS)."
    exit 1
fi

# install dependencies
log INFO "Installing system dependencies..."
apt update
apt install -y python3 python3-pip libsndfile1-dev make ffmpeg git curl

INSTALL_DIR="/opt/BotWave"
BIN_DIR="$INSTALL_DIR/bin"
SYMLINK_DIR="/usr/local/bin"

log INFO "Creating install directories..."
mkdir -p "$INSTALL_DIR/uploads"
mkdir -p "$BIN_DIR"
cd "$INSTALL_DIR"

umask 002

if [[ ! -d venv ]]; then
    log INFO "Creating Python virtual environment..."
    python3 -m venv venv
fi

create_symlink() {
    local target="$1"
    local link_name="$2"
    if [[ -e "$SYMLINK_DIR/$link_name" ]]; then
        log WARN "Removing existing symlink or file: $SYMLINK_DIR/$link_name"
        rm -f "$SYMLINK_DIR/$link_name"
    fi
    ln -s "$BIN_DIR/$link_name" "$SYMLINK_DIR/$link_name"
    log INFO "Symlink created: $SYMLINK_DIR/$link_name -> $BIN_DIR/$link_name"
}

install_client() {
    log INFO "Cloning PiFmRds..."
    git clone https://github.com/ChristopheJacquet/PiFmRds || true
    cd PiFmRds/src
    log INFO "Building PiFmRds..."
    make clean
    make
    log INFO "Installed PiFmRds"

    cd "$INSTALL_DIR"

    log INFO "Installing piwave..."
    ./venv/bin/pip install --upgrade pip
    ./venv/bin/pip install git+https://github.com/douxxtech/piwave.git
    log INFO "Installed PiWave."

    log INFO "Downloading client.py and wrapper..."
    mkdir -p "$INSTALL_DIR/client"
    curl -L https://raw.githubusercontent.com/douxxtech/botwave/main/client/client.py -o "$INSTALL_DIR/client/client.py"
    curl -L https://raw.githubusercontent.com/douxxtech/botwave/main/bin/bw-client -o "$BIN_DIR/bw-client"
    chmod +x "$BIN_DIR/bw-client"
    create_symlink "$BIN_DIR/bw-client" "bw-client"
    log INFO "Installed client.py and bw-client."
}

install_server() {
    log INFO "Downloading server.py and binary..."
    mkdir -p "$INSTALL_DIR/server"
    curl -L https://raw.githubusercontent.com/douxxtech/botwave/main/server/server.py -o "$INSTALL_DIR/server/server.py"
    curl -L https://raw.githubusercontent.com/douxxtech/botwave/main/bin/bw-server -o "$BIN_DIR/bw-server"
    chmod +x "$BIN_DIR/bw-server"
    create_symlink "$BIN_DIR/bw-server" "bw-server"
    log INFO "Installed server.py and bw-server."
}

install_binaries() {
    log INFO "Downloading binaries..."
    curl -L https://raw.githubusercontent.com/douxxtech/botwave/main/bin/bw-update -o "$BIN_DIR/bw-update"
    chmod +x "$BIN_DIR/bw-update"
    create_symlink "$BIN_DIR/bw-update" "bw-update"
    log INFO "Installed bw-update."
}

if [[ "$MODE" == "client" ]]; then
    install_client
    install_binaries
elif [[ "$MODE" == "server" ]]; then
    install_server
    install_binaries
elif [[ "$MODE" == "both" ]]; then
    install_client
    install_server
    install_binaries
fi

log INFO "Retrieving last commit"
curl -s https://api.github.com/repos/douxxtech/botwave/commits | grep '"sha":' | head -n 1 | cut -d '"' -f 4 > "$INSTALL_DIR/last_commit"

log INFO "Installation complete."

cd "$START_PWD"
