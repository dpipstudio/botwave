#!/bin/bash

# BotWave - Install script

# A program by Douxx (douxx.tech | github.com/douxxtech)
# https://github.com/douxxtech/botwave
# https://botwave.dpip.lol
# A DPIP Studios project. https://dpip.lol
# Licensed under GPL-v3.0 (see LICENSE)

# Exit on errors
set -e

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

# check if we're on a Unix-like OS
if [[ "$(uname)" != "Linux" && "$(uname)" != "Darwin" ]]; then
    log ERROR "This script must be run on a Unix-like system (Linux/macOS)."
    exit 1
fi

# install requirements
log INFO "Installing system dependencies..."
apt update
apt install -y python3 python3-pip libsndfile1-dev make ffmpeg git curl

# setup working directory
INSTALL_DIR="/opt/BotWave_Deps"
log INFO "Creating install directory at $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR/upload"
cd "$INSTALL_DIR"

umask 002

if [[ ! -d venv ]]; then
    log INFO "Creating Python virtual environment..."
    python3 -m venv venv
fi

install_client() {
    log INFO "Cloning PiFmRds..."
    git clone https://github.com/ChristopheJacquet/PiFmRds || true
    cd PiFmRds/src
    log INFO "Building PiFmRds..."
    make clean
    make
    cd "$INSTALL_DIR"

    log INFO "Installing piwave..."
    ./venv/bin/pip install --upgrade pip
    ./venv/bin/pip install git+https://github.com/douxxtech/piwave.git

    log INFO "Installing bw-client..."
    curl -L https://raw.githubusercontent.com/douxxtech/botwave/refs/heads/main/client/client.py -o /bin/bw-client
    chmod +x /bin/bw-client
}

install_server() {
    log INFO "Installing bw-server..."
    curl -L https://raw.githubusercontent.com/douxxtech/botwave/refs/heads/main/server/server.py -o /bin/bw-server
    chmod +x /bin/bw-server
}

if [[ "$MODE" == "client" ]]; then
    install_client
elif [[ "$MODE" == "server" ]]; then
    install_server
elif [[ "$MODE" == "both" ]]; then
    install_client
    install_server
fi

log INFO "Installation complete."
