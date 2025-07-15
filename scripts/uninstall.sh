#!/bin/bash

# BotWave - Uninstall script

# A program by Douxx (douxx.tech | github.com/douxxtech)
# https://github.com/douxxtech/botwave
# https://botwave.dpip.lol
# A DPIP Studios project. https://dpip.lol
# Licensed under GPL-v3.0 (see LICENSE)


# Exit on errors
set -e

# Colors
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

# remove client and server binaries
log INFO "Removing binaries..."
rm -f /bin/bw-client
rm -f /bin/bw-server
rm -f /bin/bw-update

# remove installation directory
INSTALL_DIR="/opt/BotWave_Deps"
if [[ -d "$INSTALL_DIR" ]]; then
    log INFO "Removing install directory at $INSTALL_DIR..."
    rm -rf "$INSTALL_DIR"
else
    log WARN "Install directory $INSTALL_DIR does not exist."
fi

log INFO "Uninstallation complete."
