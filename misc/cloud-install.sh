#!/bin/bash

# BotWave - Cloud Shell Quick Install
# Sets up BotWave server with bore.pub tunnels

set -e

# ============================================================================
# CONSTANTS
# ============================================================================

readonly RED='\033[0;31m'
readonly GRN='\033[0;32m'
readonly YEL='\033[1;33m'
readonly BLU='\033[0;34m'
readonly NC='\033[0m'

readonly BORE_SERVER="bore.pub"
readonly BORE_VERSION="0.6.0"

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

log() {
    local level="$1"
    shift
    local color=""

    case "$level" in
        INFO)  color="$GRN" ;;
        WARN)  color="$YEL" ;;
        ERROR) color="$RED" ;;
        *)     color="$NC" ;;
    esac

    printf "[%s] ${color}%-5s${NC} %s\n" "$(date +%T)" "$level" "$*" >&2
}

# ============================================================================
# INSTALLATION STEPS
# ============================================================================

install_bore() {
    log INFO "Installing bore..."
    
    if command -v bore &> /dev/null; then
        log INFO "bore already installed, skipping"
        return 0
    fi

    local arch=$(uname -m)
    local download_url=""

    case "$arch" in
        x86_64)
            download_url="https://github.com/ekzhang/bore/releases/download/v${BORE_VERSION}/bore-v${BORE_VERSION}-x86_64-unknown-linux-musl.tar.gz"
            ;;
        aarch64|arm64)
            download_url="https://github.com/ekzhang/bore/releases/download/v${BORE_VERSION}/bore-v${BORE_VERSION}-aarch64-unknown-linux-musl.tar.gz"
            ;;
        *)
            log ERROR "Unsupported architecture: $arch"
            exit 1
            ;;
    esac

    log INFO "Downloading bore from GitHub releases..."
    curl -sSL "$download_url" | sudo tar -xz -C /usr/local/bin
    sudo chmod +x /usr/local/bin/bore
    log INFO "bore installed successfully"
}

install_botwave() {
    log INFO "Installing BotWave server..."
    
    curl -sSL https://botwave.dpip.lol/install | sudo bash -s -- server --no-alsa
    
    log INFO "BotWave server installed"
}

create_tunnel_script() {
    local BW_INSTALL="/opt/BotWave"
    sudo mkdir -p "$BW_INSTALL/scripts/tunnels"
    sudo mkdir -p "$BW_INSTALL/handlers"

    # those paths are supposing we run this from the repo root
    # maybe fix one day

    sudo cp misc_doc/cloud_tunnels/scripts/* "$BW_INSTALL/scripts/tunnels/"
    sudo chmod +x "$BW_INSTALL/scripts/tunnels/"*.sh

    sudo cp misc_doc/cloud_tunnels/handlers/* "$BW_INSTALL/handlers/"
}

# ============================================================================
# MAIN
# ============================================================================

main() {
    echo ""
    echo "=================================="
    echo "BotWave For Cloud Shell Install"
    echo "Using bore.pub for tunnels"
    echo "=================================="
    echo ""
    
    log INFO "Starting installation..."
    
    install_bore
    
    install_botwave
    
    create_tunnel_script
    
    
    echo ""
    log INFO "Installation complete!"
    echo ""
    echo "Next steps:"
    echo "  1. Start BotWave server: bw-server"
    echo "  2. The bore.pub tunnels will start automatically"
    echo "  3. Note the assigned ports from the output"
    echo ""
}

main "$@"