#!/bin/bash

# BotWave - Update script

# A program by Douxx (douxx.tech | github.com/dpipstudio)
# https://github.com/dpipstudio/botwave
# https://botwave.dpip.lol
# A DPIP Studios project. https://dpip.lol
# Licensed under GPL-v3.0 (see LICENSE)

set -e

START_PWD=$(pwd)

RED='\033[0;31m'
GRN='\033[0;32m'
YEL='\033[1;33m'
NC='\033[0m'

GITHUB_RAW_URL="https://raw.githubusercontent.com/dpipstudio/botwave"
INSTALL_DIR="/opt/BotWave"
BIN_DIR="$INSTALL_DIR/bin"
SYMLINK_DIR="/usr/local/bin"

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

# check OS
if [[ "$(uname)" != "Linux" && "$(uname)" != "Darwin" ]]; then
    log ERROR "This script must be run on a Unix-like system (Linux/macOS)."
    exit 1
fi

create_symlink() {
    local link_name="$1"
    if [[ -e "$SYMLINK_DIR/$link_name" ]]; then
        log WARN "Removing existing symlink or file: $SYMLINK_DIR/$link_name"
        rm -f "$SYMLINK_DIR/$link_name"
    fi
    ln -s "$BIN_DIR/$link_name" "$SYMLINK_DIR/$link_name"
    log INFO "Symlink created: $SYMLINK_DIR/$link_name -> $BIN_DIR/$link_name"
}

cd "$INSTALL_DIR"

log INFO "Checking if we have to update..."

LATEST_COMMIT=$(curl -s https://api.github.com/repos/dpipstudio/botwave/commits | grep '"sha":' | head -n 1 | cut -d '"' -f 4)
CURRENT_COMMIT=$(cat "$INSTALL_DIR/last_commit" 2>/dev/null || echo "")

if [[ "$LATEST_COMMIT" != "$CURRENT_COMMIT" ]]; then
    log INFO "New version available. Updating now..."
    
    # fetch install.json from the latest commit
    log INFO "Fetching installation configuration..."
    INSTALL_JSON=$(curl -sSL "${GITHUB_RAW_URL}/${LATEST_COMMIT}/assets/installation.json?t=$(date +%s)")
    if [[ -z "$INSTALL_JSON" ]]; then
        log ERROR "Failed to fetch installation.json"
        exit 1
    fi

    download_files() {
        local section="$1"
        local file_list=$(echo "$INSTALL_JSON" | jq -r ".${section}.files[]" 2>/dev/null)
        
        if [[ -n "$file_list" ]]; then
            log INFO "Updating files for section: $section"
            while IFS= read -r file; do
                [[ -z "$file" ]] && continue
                local target_path="$INSTALL_DIR/$file"
                local target_dir=$(dirname "$target_path")
                
                mkdir -p "$target_dir"
                log INFO "  - Updating $file..."
                curl -sSL "${GITHUB_RAW_URL}/${LATEST_COMMIT}/${file}?t=$(date +%s)" -o "$target_path"
            done <<< "$file_list"
        fi
    }

    install_requirements() {
        local section="$1"
        local req_list=$(echo "$INSTALL_JSON" | jq -r ".${section}.requirements[]" 2>/dev/null)
        
        if [[ -n "$req_list" ]]; then
            log INFO "Installing Python requirements for section: $section"
            while IFS= read -r req; do
                [[ -z "$req" ]] && continue
                log INFO "  - Installing $req..."
                ./venv/bin/pip install "$req"
            done <<< "$req_list"
        fi
    }

    update_binaries() {
        local section="$1"
        local bin_list=$(echo "$INSTALL_JSON" | jq -r ".${section}.binaries[]" 2>/dev/null)
        
        if [[ -n "$bin_list" ]]; then
            log INFO "Updating binaries for section: $section"
            while IFS= read -r binary; do
                [[ -z "$binary" ]] && continue
                local bin_name=$(basename "$binary")
                local target_path="$INSTALL_DIR/$binary"
                
                mkdir -p "$(dirname "$target_path")"
                log INFO "  - Updating $binary..."
                curl -sSL "${GITHUB_RAW_URL}/${LATEST_COMMIT}/${binary}?t=$(date +%s)" -o "$target_path"
                chmod +x "$target_path"
                create_symlink "$bin_name"
            done <<< "$bin_list"
        fi
    }

    update_client_specific() {
        log INFO "Updating PiFmRds..."
        rm -rf PiFmRds
        git clone https://github.com/ChristopheJacquet/PiFmRds || true
        cd PiFmRds/src
        
        if [[ $(tr -d '\0' < /proc/device-tree/model 2>/dev/null) == *"Zero 2 W"* ]]; then
            log INFO "Detected Raspberry Pi Zero 2 W. Patching Makefile..."
            if [ -f Makefile ]; then
                sed -i 's/^RPI_VERSION :=.*/RPI_VERSION = 3/' Makefile
                log INFO "Makefile patched for Raspberry Pi Zero 2 W."
            fi
        fi
        
        make clean
        make
        cd "$INSTALL_DIR"
        log INFO "PiFmRds updated."
    }

    # update client if it exists
    if [[ -d "$INSTALL_DIR/client" ]]; then
        log INFO "Updating client components..."
        update_client_specific
        download_files "client"
        install_requirements "client"
        update_binaries "client"
        log INFO "Client updated."
    fi

    # update server if it exists
    if [[ -d "$INSTALL_DIR/server" ]]; then
        log INFO "Updating server components..."
        download_files "server"
        install_requirements "server"
        update_binaries "server"
        log INFO "Server updated."
    fi

    # always update common components
    log INFO "Updating common components..."
    download_files "always"
    install_requirements "always"
    update_binaries "always"
    log INFO "Common components updated."

    echo "$LATEST_COMMIT" > "$INSTALL_DIR/last_commit"
    log INFO "Update complete."
else
    log INFO "BotWave is already up-to-date."
fi

cd "$START_PWD"