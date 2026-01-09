#!/bin/bash

# BotWave - Uninstall Script
# A program by Douxx (douxx.tech | github.com/dpipstudio)
# https://github.com/dpipstudio/botwave
# Licensed under GPL-v3.0

set -e

# ============================================================================
# CONSTANTS & CONFIGURATION
# ============================================================================

readonly SCRIPT_VERSION="1.2.0"
readonly START_PWD=$(pwd)
readonly BANNER=$(cat <<EOF
   ___       __ _      __
  / _ )___  / /| | /| / /__ __  _____
 / _  / _ \/ __/ |/ |/ / _ \`/ |/ / -_)
/____/\___/\__/|__/|__/\_,_/|___/\__/ Uninstaller v$SCRIPT_VERSION
========================================================

EOF
)

readonly RED='\033[0;31m'
readonly GRN='\033[0;32m'
readonly YEL='\033[1;33m'
readonly NC='\033[0m'
readonly INSTALL_DIR="/opt/BotWave"
readonly SYMLINK_DIR="/usr/local/bin"
readonly TMP_DIR="/tmp/bw_uninstall"
readonly LOG_FILE="$TMP_DIR/uninstall_$(date +%s).log"

readonly SERVICES=("bw-client" "bw-server" "bw-local")
readonly BINARIES=(
    "$SYMLINK_DIR/bw-client"
    "$SYMLINK_DIR/bw-server"
    "$SYMLINK_DIR/bw-update"
    "$SYMLINK_DIR/bw-autorun"
    "$SYMLINK_DIR/bw-local"
    "$SYMLINK_DIR/bw-nandl"
)

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

confirm_uninstall() {
    log WARN "This will completely remove BotWave from your system."
    log WARN "All configuration, data, and services will be deleted."
    log WARN ""
    log WARN "Are you sure you want to continue?"
    
    export MENU_SELECT_COLOR="$RED"
    select_option "No (cancel)" "Yes (uninstall)"
    local choice=$?
    export MENU_SELECT_COLOR=""
    set -e
    
    if [[ "$choice" -eq 0 ]]; then
        log INFO "Uninstallation cancelled."
        exit 0
    fi
}

validate_installation() {
    if [[ ! -d "$INSTALL_DIR" ]]; then
        log WARN "BotWave installation not found at $INSTALL_DIR"
        log INFO "Nothing to uninstall."
        exit 0
    fi
}

# ============================================================================
# CLEANUP FUNCTIONS
# ============================================================================

stop_and_remove_services() {
    log INFO "Stopping and removing systemd services..."
    local systemd_changed=false

    for svc in "${SERVICES[@]}"; do
        if systemctl list-unit-files 2>/dev/null | grep -q "^${svc}.service"; then
            systemd_changed=true
            log INFO "  - Stopping service: ${svc}"
            silent systemctl stop "$svc" || true
            
            log INFO "  - Disabling service: ${svc}"
            silent systemctl disable "$svc" || true
            
            if [[ -f "/etc/systemd/system/${svc}.service" ]]; then
                rm -f "/etc/systemd/system/${svc}.service"
                log INFO "  - Removed service file: ${svc}.service"
            fi
        else
            log WARN "  - Service ${svc} not found, skipping"
        fi
    done

    if [[ "$systemd_changed" == true ]]; then
        log INFO "Reloading systemd daemon..."
        silent systemctl daemon-reload
        silent systemctl reset-failed || true
    else
        log INFO "No services found to remove."
    fi
}

remove_binaries() {
    log INFO "Removing binaries..."
    local found=false

    for bin in "${BINARIES[@]}"; do
        if [[ -f "$bin" ]] || [[ -L "$bin" ]]; then
            found=true
            rm -f "$bin"
            log INFO "  - Removed $(basename "$bin")"
        else
            log WARN "  - Binary not found: $(basename "$bin")"
        fi
    done

    if [[ "$found" == false ]]; then
        log INFO "No binaries found to remove."
    fi
}

remove_installation_directory() {
    log INFO "Removing installation directory..."
    
    if [[ -d "$INSTALL_DIR" ]]; then
        rm -rf "$INSTALL_DIR"
        log INFO "  - Removed $INSTALL_DIR"
    else
        log WARN "  - Installation directory not found: $INSTALL_DIR"
    fi
}

remove_alsa_loopback() {
    log INFO "Checking ALSA loopback configuration..."

    local removed=false

    for file in \
        "/etc/modules-load.d/aloop.conf" \
        "/etc/modprobe.d/aloop.conf"
    do
        if [[ -f "$file" ]] && grep -q "BotWave installer" "$file"; then
            log INFO "  - Removing BotWave ALSA config: $file"
            rm -f "$file"
            removed=true
        else
            log INFO "  - Skipping $file (not BotWave-managed)"
        fi
    done

    if [[ "$removed" == true ]]; then
        log WARN "BotWave ALSA configuration removed."
        log WARN "A reboot may be required for ALSA changes to fully apply."
    else
        log INFO "No BotWave ALSA configuration found."
    fi
}


# ============================================================================
# SUMMARY
# ============================================================================

print_summary() {
    log INFO ""
    log INFO "=========================================="
    log INFO "BotWave has been completely uninstalled."
    log INFO "=========================================="
    log INFO ""
    log INFO "Removed:"
    log INFO "  - Systemd services"
    log INFO "  - Binary files and symlinks"
    log INFO "  - Installation directory ($INSTALL_DIR)"
    log INFO "  - Temporary files"
    log INFO ""
    log INFO "Log file: $LOG_FILE"
}

# ============================================================================
# MAIN UNINSTALL FLOW
# ============================================================================

main() {
    mkdir -p "$TMP_DIR"

    echo "$BANNER"

    # Pre-flight checks
    check_root_privileges "$@"
    
    log INFO "Full log transcript will be written to $LOG_FILE"
    
    validate_installation
    confirm_uninstall

    # Perform uninstallation
    stop_and_remove_services
    remove_binaries
    remove_installation_directory
    remove_alsa_loopback

    # Summary
    print_summary

    cd "$START_PWD"
    echo "Uninstallation completed, exiting " # avoid blocking
    exit 0
}

main "$@"