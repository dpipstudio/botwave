#!/bin/bash

# BotWave - Uninstall script

# A program by Douxx (douxx.tech | github.com/dpipstudio)
# https://github.com/dpipstudio/botwave
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

# stop and remove systemd services
SERVICES=("bw-client" "bw-server" "bw-local")
SYSTEMD_CHANGED=false

for svc in "${SERVICES[@]}"; do
    if systemctl list-unit-files | grep -q "^${svc}.service"; then
        SYSTEMD_CHANGED=true
        log INFO "Stopping and disabling service: ${svc}"
        systemctl stop "$svc" 2>/dev/null || true
        systemctl disable "$svc" 2>/dev/null || true
        if [[ -f "/etc/systemd/system/${svc}.service" ]]; then
            rm -f "/etc/systemd/system/${svc}.service"
            log INFO "Removed service file: /etc/systemd/system/${svc}.service"
        fi
    else
        log WARN "Service ${svc} not found — skipping."
    fi
done

# reload systemd only if needed
if [[ "$SYSTEMD_CHANGED" == true ]]; then
    log INFO "Reloading systemd daemon..."
    systemctl daemon-reload
    systemctl reset-failed 2>/dev/null || true
fi

# remove binaries
log INFO "Removing binaries..."
BINARIES=(
    /usr/local/bin/bw-client
    /usr/local/bin/bw-server
    /usr/local/bin/bw-update
    /usr/local/bin/bw-autorun
    /usr/local/bin/bw-local
    /usr/local/bin/bw-nandl
)

for bin in "${BINARIES[@]}"; do
    if [[ -f "$bin" ]]; then
        rm -f "$bin"
        log INFO "Removed $bin"
    else
        log WARN "Binary not found: $bin"
    fi
done

# remove installation directory
INSTALL_DIR="/opt/BotWave"
if [[ -d "$INSTALL_DIR" ]]; then
    log INFO "Removing install directory at $INSTALL_DIR..."
    rm -rf "$INSTALL_DIR"
else
    log WARN "Install directory $INSTALL_DIR does not exist."
fi

# done
log INFO "System cleanup complete."
log INFO "Uninstallation of BotWave is complete."
