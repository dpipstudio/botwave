#!/bin/bash

# BotWave - Install script

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

GITHUB_RAW_URL="https://raw.githubusercontent.com/dpipstudio/botwave/main"
INSTALL_DIR="/opt/BotWave"
BIN_DIR="$INSTALL_DIR/bin"
BACKENDS_DIR="$INSTALL_DIR/backends"
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
apt update -qq
apt install -qq -y python3 python3-pip python3-venv libsndfile1-dev make ffmpeg git curl jq

log INFO "Creating install directories..."
mkdir -p "$INSTALL_DIR/uploads"
mkdir -p "$INSTALL_DIR/handlers"
mkdir -p "$BIN_DIR"
mkdir -p "$BACKENDS_DIR"
cd "$INSTALL_DIR"

umask 002

if [[ ! -d venv ]]; then
    log INFO "Creating Python virtual environment..."
    python3 -m venv venv
    log INFO "Updating PIP in the virtual environment..."
    ./venv/bin/pip install --upgrade pip > /dev/null
fi

# fetch install.json
log INFO "Fetching installation configuration..."
INSTALL_JSON=$(curl -sSL "${GITHUB_RAW_URL}/assets/installation.json?t=$(date +%s)")
if [[ -z "$INSTALL_JSON" ]]; then
    log ERROR "Failed to fetch installation.json"
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

download_files() {
    local section="$1"
    local file_list=$(echo "$INSTALL_JSON" | jq -r ".${section}.files[]" 2>/dev/null)
    
    if [[ -n "$file_list" ]]; then
        log INFO "Downloading files for : $section"
        while IFS= read -r file; do
            [[ -z "$file" ]] && continue
            local target_path="$INSTALL_DIR/$file"
            local target_dir=$(dirname "$target_path")
            
            mkdir -p "$target_dir"
            log INFO "  - Downloading $file..."
            curl -sSL "${GITHUB_RAW_URL}/${file}?t=$(date +%s)" -o "$target_path"
        done <<< "$file_list"
    fi
}

install_requirements() {
    local section="$1"
    local req_list=$(echo "$INSTALL_JSON" | jq -r ".${section}.requirements[]" 2>/dev/null)
    
    if [[ -n "$req_list" ]]; then
        log INFO "Installing Python requirements for : $section"
        while IFS= read -r req; do
            [[ -z "$req" ]] && continue
            log INFO "  - Installing $req..."
            ./venv/bin/pip install "$req" > /dev/null
        done <<< "$req_list"
    fi
}

install_binaries() {
    local section="$1"
    local bin_list=$(echo "$INSTALL_JSON" | jq -r ".${section}.binaries[]" 2>/dev/null)
    
    if [[ -n "$bin_list" ]]; then
        log INFO "Installing binaries for : $section"
        while IFS= read -r binary; do
            [[ -z "$binary" ]] && continue
            local bin_name=$(basename "$binary")
            local target_path="$INSTALL_DIR/$binary"
            
            mkdir -p "$(dirname "$target_path")"
            log INFO "  - Downloading $binary..."
            curl -sSL "${GITHUB_RAW_URL}/${binary}?t=$(date +%s)" -o "$target_path"
            chmod +x "$target_path"
            create_symlink "$bin_name"
        done <<< "$bin_list"
    fi
}

install_backends() {
    local backend_list=$(echo "$INSTALL_JSON" | jq -r ".backends[]" 2>/dev/null)
    
    if [[ -z "$backend_list" ]]; then
        log WARN "No backends found in installation.json"
        return
    fi
    
    log INFO "Installing backends..."
    cd "$BACKENDS_DIR"
    
    while IFS= read -r repo_url; do
        [[ -z "$repo_url" ]] && continue
        
        local repo_name=$(basename "$repo_url" .git)
        log INFO "  - Processing backend: $repo_name"
        
        if [[ -d "$repo_name" ]]; then
            log INFO "    Backend $repo_name already exists, skipping clone" # shoudltn happen
        else
            log INFO "    Cloning $repo_name..."
            git clone --quiet "$repo_url" || {
                log ERROR "    Failed to clone $repo_name"
                continue
            }
        fi
        
        cd "$repo_name"
        
        if [[ -d "src" ]]; then
            log INFO "    Building $repo_name..."
            cd src

            make -s clean
            make -s || {
                log ERROR "    Failed to build $repo_name"
                cd "$BACKENDS_DIR"
                continue
            }
            log INFO "    Successfully built $repo_name"
            cd ..
        else
            log WARN "    No src directory found in $repo_name, skipping build"
        fi
        
        cd "$BACKENDS_DIR"
    done <<< "$backend_list"
    
    cd "$INSTALL_DIR"
}

# what to install
SECTIONS_TO_INSTALL=()

if [[ "$MODE" == "both" ]]; then
    log INFO "Installing both client and server"
    SECTIONS_TO_INSTALL+=("client" "server")
else
    SECTIONS_TO_INSTALL+=("$MODE")
fi

# add 'always' section
SECTIONS_TO_INSTALL+=("always")

# install backends if client mode is selected
if [[ "$MODE" == "client" || "$MODE" == "both" ]]; then
    install_backends
fi

for section in "${SECTIONS_TO_INSTALL[@]}"; do
    log INFO "Processing : $section"
    download_files "$section"
    install_requirements "$section"
    install_binaries "$section"
done

log INFO "Retrieving last commit..."
curl -s https://api.github.com/repos/dpipstudio/botwave/commits | grep '"sha":' | head -n 1 | cut -d '"' -f 4 > "$INSTALL_DIR/last_commit"

log INFO "Installation complete."
log INFO "Installed components:"
[[ "$MODE" == "client" || "$MODE" == "both" ]] && log INFO "  - Client mode"
[[ "$MODE" == "server" || "$MODE" == "both" ]] && log INFO "  - Server mode"
log INFO "  - Common utilities"

cd "$START_PWD"