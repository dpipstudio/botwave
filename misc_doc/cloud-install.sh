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
    log INFO "Creating bore tunnel script..."
    
    local script_dir="/opt/BotWave/cloudtunnel"
    local script_file="$script_dir/tunnel.sh"
    
    sudo mkdir -p "$script_dir"
    
    sudo tee "$script_file" > /dev/null <<'EOF'
#!/bin/bash

# BotWave bore.pub Tunnel Starter


echo "Starting bore.pub tunnels..."
echo "This will expose your BotWave server to the internet."
echo ""

pkill bore 2>/dev/null || true
sleep 1

# Start tunnels (bore.pub assigns random ports)
bore local 9938 --to bore.pub > /tmp/bore_9938.log 2>&1 &
echo $! > /tmp/bore_9938.pid

bore local 9921 --to bore.pub > /tmp/bore_9921.log 2>&1 &
echo $! > /tmp/bore_9921.pid

sleep 1

echo ""
echo "=========================================="
WS_PORT=$(grep -oP 'listening at bore.pub:\K\d+' /tmp/bore_9938.log 2>/dev/null | head -1)
HTTP_PORT=$(grep -oP 'listening at bore.pub:\K\d+' /tmp/bore_9921.log 2>/dev/null | head -1)

if [ -n "$WS_PORT" ] && [ -n "$HTTP_PORT" ]; then
    echo "WebSocket: bore.pub:$WS_PORT (local 9938)"
    echo "HTTP:      bore.pub:$HTTP_PORT (local 9921)"
    echo "=========================================="
    echo ""
    echo "Connect with: sudo bw-client bore.pub --port $WS_PORT --fport $HTTP_PORT"
    echo ""
else
    echo "Error: Could not get tunnel ports."
    echo "Check logs:"
    echo "  /tmp/bore_9938.log"
    echo "  /tmp/bore_9921.log"
fi
echo "=========================================="

# Tunnels will continue running in background
# No 'wait' needed - let bw-server continue
EOF

    sudo chmod +x "$script_file"
    log INFO "Tunnel script created at $script_file"
}

create_tunnel_handler() {
    log INFO "Creating tunnel handler..."
    
    local handler_file="/opt/BotWave/handlers/s_onready.shdl"
    
    sudo mkdir -p "$(dirname "$handler_file")"
    
    sudo tee "$handler_file" > /dev/null <<'EOF'
# BotWave Server Ready Handler
# Automatically starts bore.pub tunnels when server is ready
< echo "=========================================="
< echo "BotWave Server Started!"
< echo "=========================================="
< echo ""
< echo "Launching tunnels, please wait."
< bash /opt/BotWave/cloudtunnel/tunnel.sh
EOF

    log INFO "Tunnel handler created at $handler_file"
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
    
    create_tunnel_handler
    
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