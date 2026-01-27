#!/bin/bash

# BotWave - Installation Script
# A program by Douxx (douxx.tech | github.com/dpipstudio)
# https://github.com/dpipstudio/botwave
# Licensed under GPL-v3.0

set -e

# ============================================================================
# CONSTANTS & CONFIGURATION
# ============================================================================

readonly SCRIPT_VERSION="1.3.0"
readonly START_PWD=$(pwd)
readonly BANNER=$(cat <<EOF
   ___       __ _      __
  / _ )___  / /| | /| / /__ __  _____
 / _  / _ \/ __/ |/ |/ / _ \`/ |/ / -_)
/____/\___/\__/|__/|__/\_,_/|___/\__/ Installer v$SCRIPT_VERSION
======================================================

EOF
)

readonly RED='\033[0;31m'
readonly GRN='\033[0;32m'
readonly YEL='\033[1;33m'
readonly NC='\033[0m'
readonly GITHUB_RAW_URL="https://raw.githubusercontent.com/dpipstudio/botwave"
readonly INSTALL_DIR="/opt/BotWave"
readonly BIN_DIR="$INSTALL_DIR/bin"
readonly BACKENDS_DIR="$INSTALL_DIR/backends"
readonly SYMLINK_DIR="/usr/local/bin"
readonly TMP_DIR="/tmp/bw_install"
readonly LOG_FILE="$TMP_DIR/install_$(date +%s).log"
readonly VALID_MODES=("client" "server" "both")
readonly ALSA_MODULES_CONF="/etc/modules-load.d/aloop.conf"
readonly ALSA_MODPROBE_CONF="/etc/modprobe.d/aloop.conf"

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

    printf "[%s] ${color}%-5s${NC} %s\n" "$(date +%T)" "$level" "$*" | tee -a "$LOG_FILE" >&2 || true
}

silent() {
    "$@" >> "$LOG_FILE" 2>&1
}

# ============================================================================
# ARGUMENT PARSING
# ============================================================================

parse_arguments() {
    TARGET_VERSION=""
    USE_LATEST=false
    INSTALL_MODE=""
    SETUP_ALSA=""


    while [[ $# -gt 0 ]]; do
        case $1 in
            -l|--latest)
                USE_LATEST=true
                shift
                ;;
            -t|--to)
                if [[ -z "$2" ]] || [[ "$2" == -* ]]; then
                    log ERROR "Option --to requires a version argument"
                    exit 1
                fi
                TARGET_VERSION="$2"
                shift 2
                ;;
            --alsa)
                SETUP_ALSA=true
                shift
                ;;
            --no-alsa)
                SETUP_ALSA=false
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            client|server|both)
                INSTALL_MODE="$1"
                shift
                ;;
            *)
                log ERROR "Unknown option: $1"
                log INFO "Did you mean one of these?"
                log INFO "  client              Install client components"
                log INFO "  server              Install server components"
                log INFO "  both                Install both client and server"
                log INFO "  -l, --latest        Install from latest commit (unreleased)"
                log INFO "  -t, --to <version>  Install specific release version"
                log INFO "  --[no-]alsa          Setup ALSA loopback card"
                log INFO "  -h, --help          Show help message"
                exit 1
                ;;
        esac
    done
}

show_help() {
    cat << EOF
BotWave Installation Script v$SCRIPT_VERSION

Usage: $(basename "$0") [MODE] [OPTIONS]

Modes:
  client              Install client components
  server              Install server components
  both                Install both client and server components

Options:
  -l, --latest        Install from the latest commit (even if unreleased)
  -t, --to <version>  Install a specific release version
  -h, --help          Show this help message

Examples:
  $(basename "$0") client                    # Install client (latest release)
  $(basename "$0") both --latest             # Install both (latest commit)
  $(basename "$0") server --to v1.0.0-oak

EOF
}

# ============================================================================
# INTERACTIVE MENU SYSTEM
# ============================================================================

select_option() {
    # Credit: https://unix.stackexchange.com/questions/146570/arrow-key-enter-menu
    set +e

    # Handle non-interactive environments
    if [[ -e /dev/tty ]]; then
        exec < /dev/tty > /dev/tty
    elif [[ ! -t 0 ]] || [[ ! -t 1 ]]; then
        _fallback_menu "$@"
        return $?
    fi

    _arrow_key_menu "$@"
    local result=$?
    return $result
}

_fallback_menu() {
    local idx=1
    for opt; do
        echo "  $idx) $opt" >&2
        ((idx++))
    done

    while true; do
        echo -n "Enter number (1-$#): " >&2
        read selection

        if [[ "$selection" =~ ^[0-9]+$ ]] &&
           [ "$selection" -ge 1 ] &&
           [ "$selection" -le $# ]; then
            return $((selection - 1))
        else
            echo "Invalid selection. Please enter a number between 1 and $#." >&2
        fi
    done
}

_arrow_key_menu() {
    local ESC=$(printf "\033")
    local MENU_SELECT_COLOR="${MENU_SELECT_COLOR:-$ESC[94m}"
    local MENU_UNSELECT_COLOR="${MENU_UNSELECT_COLOR:-$NC}"

    cursor_blink_on()  { printf "$ESC[?25h"; }
    cursor_blink_off() { printf "$ESC[?25l"; }
    cursor_to()        { printf "$ESC[$1;${2:-1}H"; }
    print_option()     { printf "  ${MENU_UNSELECT_COLOR}$1${NC}"; }
    print_selected()   { printf "${MENU_SELECT_COLOR}> $1${NC}"; }
    get_cursor_row()   { IFS=';' read -sdR -p $'\E[6n' ROW COL; echo ${ROW#*[}; }
    key_input() {
        read -s -n3 key 2>/dev/null >&2
        if [[ $key = $ESC[A ]]; then echo up; fi
        if [[ $key = $ESC[B ]]; then echo down; fi
        if [[ $key = "" ]]; then echo enter; fi
    }

    # Print blank lines for menu
    for opt; do printf "\n"; done

    local lastrow=$(get_cursor_row)
    local startrow=$(($lastrow - $#))

    trap "cursor_blink_on; stty echo; printf '\n'; exit" 2
    cursor_blink_off

    local selected=0
    while true; do
        local idx=0
        for opt; do
            cursor_to $(($startrow + $idx))
            if [ $idx -eq $selected ]; then
                print_selected "$opt"
            else
                print_option "$opt"
            fi
            ((idx++))
        done

        case $(key_input) in
            enter) break;;
            up)    ((selected--));
                   if [ $selected -lt 0 ]; then selected=$(($# - 1)); fi;;
            down)  ((selected++));
                   if [ $selected -ge $# ]; then selected=0; fi;;
        esac
    done

    cursor_to $lastrow
    printf "\n"
    cursor_blink_on
    return $selected
}

# ============================================================================
# VALIDATION FUNCTIONS
# ============================================================================

check_root_privileges() {
    if [[ "$EUID" -ne 0 ]]; then
        if [[ ! -t 0 ]]; then
            log WARN "This script must be run as root. Please run it again with sudo."
            exit 1
        fi

        log WARN "This script must be run as root. Re-run with sudo?"
        export MENU_SELECT_COLOR="$RED"
        select_option "Yes (sudo)" "No (exit)"
        local choice=$?
        set -e

        if [[ "$choice" -eq 0 ]]; then
            log WARN "Restarting with sudo..."
            sudo bash "$0" "$@"
            exit $?
        else
            log ERROR "Root privileges required. Exiting."
            exit 1
        fi
    fi
}

validate_os() {
    source /etc/os-release

    if ! [[ "$ID_LIKE" == *"debian"* || "$ID" == "debian" ]]; then
        log ERROR "This doesn't seem to be a Debian-based Linux distribution."
        log WARN "Installation may not work as expected on this system."
        log WARN "Continue anyway?"

        export MENU_SELECT_COLOR="$RED"
        select_option "No (exit)" "Yes (continue)"

        if [[ $? -eq 0 ]]; then
            exit 1
        fi

        set -e
    fi
}

validate_hardware() {
    local mode="$1"

    if [[ "$mode" != "client" && "$mode" != "both" ]]; then
        return 0
    fi

    local model="$(tr -d '\0' </proc/device-tree/model 2>/dev/null)"
    local supported=false

    if echo "$model" | grep -qi "raspberry pi"; then
        if ! echo "$model" | grep -qiE "raspberry pi [5-9]"; then
            supported=true
        fi
    fi

    if [[ "$supported" == false ]]; then
        log ERROR "Unsupported device detected."
        log WARN "This program requires a Raspberry Pi (models 1-4, Zero) but not Pi 5 or newer."
        log WARN "Continue anyway?"

        export MENU_SELECT_COLOR="$RED"
        select_option "No (exit)" "Yes (continue)"

        if [[ $? -eq 0 ]]; then
            exit 1
        fi

        export MENU_SELECT_COLOR=""

        set -e
    fi
}

prompt_alsa_setup() {
    local mode="$1"
    
    if [[ -n "$SETUP_ALSA" ]]; then
        return 0
    fi
    
    log INFO "Setup ALSA loopback card for live streaming?"
    log INFO "(This will create/overwrite /etc/modules-load.d/aloop.conf and /etc/modprobe.d/aloop.conf)"
    select_option "No" "Yes"
    
    if [[ $? -eq 1 ]]; then
        SETUP_ALSA=true
    else
        SETUP_ALSA=false
    fi
    
    set -e
}

# ============================================================================
# VERSION MANAGEMENT
# ============================================================================

resolve_target_commit() {
    if [[ "$USE_LATEST" == true ]]; then
        log INFO "Fetching latest commit..."
        local latest_commit=$(curl -sSL https://api.github.com/repos/dpipstudio/botwave/commits | \
            grep '"sha":' | \
            head -n 1 | \
            cut -d '"' -f 4)

        if [[ -z "$latest_commit" ]]; then
            log ERROR "Failed to fetch latest commit"
            exit 1
        fi

        log INFO "Latest commit: ${latest_commit:0:7}"
        echo "$latest_commit"
        return 0
    fi

    if [[ -n "$TARGET_VERSION" ]]; then
        log INFO "Looking up release: $TARGET_VERSION"
        local install_json=$(curl -sSL "${GITHUB_RAW_URL}/main/assets/installation.json?t=$(date +%s)")
        local commit=$(echo "$install_json" | jq -r ".releases[] | select(.codename==\"$TARGET_VERSION\") | .commit")

        if [[ -z "$commit" ]]; then
            log ERROR "Release '$TARGET_VERSION' not found"
            log INFO "Available releases:"
            echo "$install_json" | jq -r '.releases[].codename' | while read -r rel; do
                log INFO "  - $rel"
            done
            exit 1
        fi

        log INFO "Found commit: ${commit:0:7}"
        echo "$commit"
        return 0
    fi

    # Default: latest release
    log INFO "Fetching latest release..."
    local install_json=$(curl -sSL "${GITHUB_RAW_URL}/main/assets/installation.json?t=$(date +%s)")
    local latest_release_commit=$(echo "$install_json" | jq -r '.releases[0].commit')

    if [[ -z "$latest_release_commit" ]]; then
        log ERROR "Failed to fetch latest release"
        exit 1
    fi

    local codename=$(echo "$install_json" | jq -r '.releases[0].codename')
    log INFO "Latest release: $codename (${latest_release_commit:0:7})"
    echo "$latest_release_commit"
}

# ============================================================================
# SYSTEM SETUP
# ============================================================================

install_system_dependencies() {
    log INFO "Installing system dependencies..."
    silent apt update
    silent apt install -y \
        python3 \
        python3-pip \
        python3-venv \
        python3-dev \
        libsndfile1-dev \
        libasound2-dev \
        libffi-dev \
        libssl-dev \
        build-essential \
        make \
        ffmpeg \
        git \
        curl \
        jq
}

setup_directory_structure() {
    log INFO "Creating directory structure..."
    mkdir -p "$INSTALL_DIR/uploads"
    mkdir -p "$INSTALL_DIR/handlers"
    mkdir -p "$BIN_DIR"
    mkdir -p "$BACKENDS_DIR"
    cd "$INSTALL_DIR"
    umask 002
}

setup_python_environment() {
    if [[ ! -d venv ]]; then
        log INFO "Creating Python virtual environment..."
        silent python3 -m venv venv
        log INFO "Upgrading pip..."
        silent ./venv/bin/pip install --upgrade pip
    else
        log INFO "Python virtual environment already exists."
    fi
}

setup_alsa_loopback() {
    if [[ "$SETUP_ALSA" != true ]]; then
        return 0
    fi

    log INFO "Setting up ALSA loopback card..."

    log INFO "Creating $ALSA_MODULES_CONF"
    mkdir -p "$(dirname "$ALSA_MODULES_CONF")"
    cat > "$ALSA_MODULES_CONF" <<EOF
# This file was generated by the BotWave installer
# See https://github.com/dpipstudio/botwave
# ============================================================

snd-aloop
EOF

    log INFO "Creating $ALSA_MODPROBE_CONF"
    mkdir -p "$(dirname "$ALSA_MODPROBE_CONF")"
    cat > "$ALSA_MODPROBE_CONF" <<EOF
# This file was generated by the BotWave installer
# See https://github.com/dpipstudio/botwave
# ============================================================

options snd-aloop index=10 id=BotWave pcm_substreams=1,1
EOF

    log INFO "ALSA loopback card configuration complete"
}


# ============================================================================
# INSTALLATION CONFIGURATION
# ============================================================================

fetch_installation_config() {
    local commit="$1"
    log INFO "Fetching installation configuration..."
    local config=$(curl -sSL "${GITHUB_RAW_URL}/${commit}/assets/installation.json?t=$(date +%s)")

    if [[ -z "$config" ]]; then
        log ERROR "Failed to fetch installation.json"
        exit 1
    fi

    echo "$config"
}

# ============================================================================
# FILE OPERATIONS
# ============================================================================

create_symlink() {
    local link_name="$1"

    if [[ -e "$SYMLINK_DIR/$link_name" ]]; then
        log WARN "Removing existing symlink: $SYMLINK_DIR/$link_name"
        rm -f "$SYMLINK_DIR/$link_name"
    fi

    ln -s "$BIN_DIR/$link_name" "$SYMLINK_DIR/$link_name"
    log INFO "Symlink created: $link_name"
}

download_files() {
    local section="$1"
    local install_json="$2"
    local commit="$3"
    local file_list=$(echo "$install_json" | jq -r ".${section}.files[]?" 2>/dev/null)

    if [[ -z "$file_list" ]]; then
        return 0
    fi

    log INFO "Downloading files for: $section"
    while IFS= read -r file; do
        [[ -z "$file" ]] && continue

        local target_path="$INSTALL_DIR/$file"
        local target_dir=$(dirname "$target_path")

        mkdir -p "$target_dir"
        log INFO "  - $file"
        silent curl -SL "${GITHUB_RAW_URL}/${commit}/${file}?t=$(date +%s)" -o "$target_path"
    done <<< "$file_list"
}

install_requirements() {
    local section="$1"
    local install_json="$2"
    local req_list=$(echo "$install_json" | jq -r ".${section}.requirements[]?" 2>/dev/null)

    if [[ -z "$req_list" ]]; then
        return 0
    fi

    log INFO "Installing Python requirements for: $section"
    while IFS= read -r req; do
        [[ -z "$req" ]] && continue
        log INFO "  - $req"
        silent ./venv/bin/pip install "$req"
    done <<< "$req_list"
}

install_binaries() {
    local section="$1"
    local install_json="$2"
    local commit="$3"
    local bin_list=$(echo "$install_json" | jq -r ".${section}.binaries[]?" 2>/dev/null)

    if [[ -z "$bin_list" ]]; then
        return 0
    fi

    log INFO "Installing binaries for: $section"
    while IFS= read -r binary; do
        [[ -z "$binary" ]] && continue

        local bin_name=$(basename "$binary")
        local target_path="$INSTALL_DIR/$binary"

        mkdir -p "$(dirname "$target_path")"
        log INFO "  - $binary"
        silent curl -SL "${GITHUB_RAW_URL}/${commit}/${binary}?t=$(date +%s)" -o "$target_path"
        chmod +x "$target_path"
        create_symlink "$bin_name"
    done <<< "$bin_list"
}

# ============================================================================
# BACKEND INSTALLATION
# ============================================================================

install_backends() {
    local install_json="$1"
    local backend_list=$(echo "$install_json" | jq -r ".backends[]?" 2>/dev/null)

    if [[ -z "$backend_list" ]]; then
        log WARN "No backends found in configuration"
        return 0
    fi

    log INFO "Installing backends..."
    cd "$BACKENDS_DIR"

    while IFS= read -r repo_url; do
        [[ -z "$repo_url" ]] && continue

        local repo_name=$(basename "$repo_url" .git)
        log INFO "  - Processing: $repo_name"

        if [[ -d "$repo_name" ]]; then
            log INFO "    Already exists, skipping clone"
        else
            log INFO "    Cloning repository..."
            silent git clone "$repo_url" || {
                log ERROR "    Failed to clone $repo_name"
                continue
            }
        fi

        cd "$repo_name"

        if [[ -d "src" ]]; then
            log INFO "    Building..."
            cd src
            silent make clean
            silent make || {
                log ERROR "    Build failed"
                cd "$BACKENDS_DIR"
                continue
            }
            log INFO "    Build successful"
            cd ..
        else
            log WARN "    No src directory, skipping build"
        fi

        cd "$BACKENDS_DIR"
    done <<< "$backend_list"

    cd "$INSTALL_DIR"
}

# ============================================================================
# COMPONENT INSTALLATION
# ============================================================================

install_components() {
    local mode="$1"
    local install_json="$2"
    local commit="$3"
    local sections=()

    # Show version info
    if [[ -n "$TARGET_VERSION" ]]; then
        log INFO "Target version: $TARGET_VERSION"
    elif [[ "$USE_LATEST" == true ]]; then
        log WARN "Using latest commit (unreleased)"
    else
        local codename=$(echo "$install_json" | jq -r '.releases[0].codename')
        log INFO "Installing release: $codename"
    fi

    # Determine sections to install
    if [[ "$mode" == "both" ]]; then
        sections=("client" "server" "always")
    else
        sections=("$mode" "always")
    fi

    # Install backends if client mode
    if [[ "$mode" == "client" || "$mode" == "both" ]]; then
        install_backends "$install_json"
    fi

    # Install each section
    for section in "${sections[@]}"; do
        log INFO "Processing section: $section"
        download_files "$section" "$install_json" "$commit"
        install_requirements "$section" "$install_json"
        install_binaries "$section" "$install_json" "$commit"
    done
}

# ============================================================================
# POST-INSTALLATION
# ============================================================================

save_version_info() {
    local commit="$1"
    log INFO "Saving version information..."
    echo "$commit" > "$INSTALL_DIR/last_commit"

    # Save release info if applicable
    if [[ -n "$TARGET_VERSION" ]]; then
        echo "$TARGET_VERSION" > "$INSTALL_DIR/last_release"
    elif [[ "$USE_LATEST" != true ]]; then
        local install_json=$(curl -sSL "${GITHUB_RAW_URL}/main/assets/installation.json?t=$(date +%s)")
        local codename=$(echo "$install_json" | jq -r ".releases[] | select(.commit==\"$commit\") | .codename")
        if [[ -n "$codename" ]]; then
            echo "$codename" > "$INSTALL_DIR/last_release"
        fi
    fi
}

print_summary() {
    local mode="$1"

    log INFO "Installation complete!"
    log INFO ""
    log INFO "Installed components:"
    [[ "$mode" == "client" || "$mode" == "both" ]] && log INFO "  - Client mode"
    [[ "$mode" == "server" || "$mode" == "both" ]] && log INFO "  - Server mode"
    log INFO "  - Common utilities"
    log INFO ""
    if [[ "$SETUP_ALSA" == true ]]; then
        log WARN "ALSA loopback card has been configured."
        log WARN "You must REBOOT for the changes to take effect!"
    fi
    log INFO "Installation directory: $INSTALL_DIR"
    log INFO "Log file: $LOG_FILE"
}

# ============================================================================
# MAIN INSTALLATION FLOW
# ============================================================================

main() {
    mkdir -p "$TMP_DIR"

    echo "$BANNER"

    # Parse command line arguments first
    parse_arguments "$@"

    # Pre-flight checks
    check_root_privileges

    log INFO "Full log transcript will be written in $LOG_FILE"

    validate_os

    # find installation mode
    local mode="$INSTALL_MODE"
    if [[ -z "$mode" ]] || [[ ! " ${VALID_MODES[*]} " == *" $mode "* ]]; then
        if [[ -n "$mode" ]]; then
            log WARN "Invalid installation mode: $mode"
        fi
        log INFO "Select installation type:"
        select_option "Client Unit" "Server Unit" "Both Units"
        mode="${VALID_MODES[$?]}"
        set -e
    fi

    log INFO "Installation mode: $mode"

    # Hardware validation
    validate_hardware "$mode"

    # Setup sound card
    prompt_alsa_setup "$mode"

    # System setup 1
    install_system_dependencies

    # Find target commit
    local target_commit
    target_commit=$(resolve_target_commit) || exit 1

    # System setup 2
    setup_directory_structure
    setup_python_environment
    setup_alsa_loopback

    # Fetch configuration and install
    local install_json=$(fetch_installation_config "$target_commit")
    install_components "$mode" "$install_json" "$target_commit"

    # Finalize
    save_version_info "$target_commit"
    print_summary "$mode"

    cd "$START_PWD"
    echo "Installation completed, exiting " # avoid blocking
    exit 0
}

main "$@"