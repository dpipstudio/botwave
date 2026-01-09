#!/bin/bash

# BotWave - Update Script
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
/____/\___/\__/|__/|__/\_,_/|___/\__/ Updater v$SCRIPT_VERSION
=====================================================

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
readonly TMP_DIR="/tmp/bw_update"
readonly LOG_FILE="$TMP_DIR/update_$(date +%s).log"

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
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                log ERROR "Unknown option: $1"
                log INFO "Did you mean one of these?"
                log INFO "  -l, --latest        Update to latest commit (unreleased)"
                log INFO "  -t, --to <version>  Update to specific release version"
                log INFO "  -h, --help          Show help message"
                exit 1
                ;;
        esac
    done
}

show_help() {
    cat << EOF
BotWave Update Script v$SCRIPT_VERSION

Usage: $(basename "$0") [OPTIONS]

Options:
  -l, --latest        Update to the latest commit (even if unreleased)
  -t, --to <version>  Update to a specific release version
  -h, --help          Show this help message

Examples:
  $(basename "$0")                    # Update to latest release
  $(basename "$0") --latest           # Update to latest commit
  $(basename "$0") --to v1.0.0-oak

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

validate_installation() {
    if [[ ! -d "$INSTALL_DIR" ]]; then
        log ERROR "BotWave installation not found at $INSTALL_DIR"
        log WARN "Would you like to run the installer?"
        
        export MENU_SELECT_COLOR="$GRN"
        select_option "Yes (install now)" "No (exit)"
        local choice=$?
        export MENU_SELECT_COLOR=""
        set -e
        
        if [[ "$choice" -eq 0 ]]; then
            log INFO "Launching installer..."
            curl -sSL https://botwave.dpip.lol/install | bash
            exit $?
        else
            log ERROR "Installation required. Exiting."
            exit 1
        fi
    fi

    if [[ ! -f "$INSTALL_DIR/last_commit" ]]; then
        log WARN "No version information found. Creating one..."
        touch "$INSTALL_DIR/last_commit"
    fi
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

    log INFO "Updating files for: $section"
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

    log INFO "Updating Python requirements for: $section"
    while IFS= read -r req; do
        [[ -z "$req" ]] && continue
        log INFO "  - $req"
        silent ./venv/bin/pip install "$req"
    done <<< "$req_list"
}

update_binaries() {
    local section="$1"
    local install_json="$2"
    local commit="$3"
    local bin_list=$(echo "$install_json" | jq -r ".${section}.binaries[]?" 2>/dev/null)

    if [[ -z "$bin_list" ]]; then
        return 0
    fi

    log INFO "Updating binaries for: $section"
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
# BACKEND UPDATES
# ============================================================================

update_backends() {
    local install_json="$1"
    local backend_list=$(echo "$install_json" | jq -r ".backends[]?" 2>/dev/null)

    if [[ -z "$backend_list" ]]; then
        log WARN "No backends found in configuration"
        return 0
    fi

    log INFO "Updating backends..."
    mkdir -p "$BACKENDS_DIR"
    cd "$BACKENDS_DIR"

    while IFS= read -r repo_url; do
        [[ -z "$repo_url" ]] && continue

        local repo_name=$(basename "$repo_url" .git)
        log INFO "  - Processing: $repo_name"

        if [[ -d "$repo_name" ]]; then
            log INFO "    Checking for updates..."
            cd "$repo_name"

            local before_commit=$(git rev-parse HEAD 2>/dev/null || echo "")

            silent git pull || {
                log ERROR "    Failed to pull updates"
                cd "$BACKENDS_DIR"
                continue
            }

            local after_commit=$(git rev-parse HEAD 2>/dev/null || echo "")

            if [[ "$before_commit" != "$after_commit" ]]; then
                log INFO "    Changes detected, rebuilding..."

                if [[ -d "src" ]]; then
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
            else
                log INFO "    No changes detected"
            fi

            cd "$BACKENDS_DIR"
        else
            log INFO "    Not found, cloning..."
            silent git clone "$repo_url" || {
                log ERROR "    Failed to clone"
                continue
            }

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
        fi
    done <<< "$backend_list"

    cd "$INSTALL_DIR"
}

# ============================================================================
# VERSION MANAGEMENT
# ============================================================================

check_for_updates() {
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
        
        local current_commit=$(cat "$INSTALL_DIR/last_commit" 2>/dev/null || echo "")
        
        if [[ "$latest_commit" == "$current_commit" ]]; then
            log INFO "Already on the latest commit."
            return 1
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
        
        local current_commit=$(cat "$INSTALL_DIR/last_commit" 2>/dev/null || echo "")
        
        if [[ "$commit" == "$current_commit" ]]; then
            log INFO "Already on version $TARGET_VERSION"
            return 1
        fi
        
        log INFO "Found commit: ${commit:0:7}"
        echo "$commit"
        return 0
    fi
    
    # Default: latest release
    log INFO "Checking for updates..."
    local install_json=$(curl -sSL "${GITHUB_RAW_URL}/main/assets/installation.json?t=$(date +%s)")
    local latest_release_commit=$(echo "$install_json" | jq -r '.releases[0].commit')
    
    if [[ -z "$latest_release_commit" ]]; then
        log ERROR "Failed to fetch latest release"
        exit 1
    fi
    
    local current_commit=$(cat "$INSTALL_DIR/last_commit" 2>/dev/null || echo "")
    
    if [[ "$latest_release_commit" == "$current_commit" ]]; then
        log INFO "BotWave is already up-to-date."
        return 1
    fi
    
    local codename=$(echo "$install_json" | jq -r '.releases[0].codename')
    log INFO "New release available: $codename (${latest_release_commit:0:7})"
    echo "$latest_release_commit"
}

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
    else
        # Clear release info if on latest commit
        rm -f "$INSTALL_DIR/last_release"
    fi
}

# ============================================================================
# COMPONENT UPDATES
# ============================================================================

update_components() {
    local install_json="$1"
    local commit="$2"

    # Show version info
    if [[ -n "$TARGET_VERSION" ]]; then
        log INFO "Target version: $TARGET_VERSION"
    elif [[ "$USE_LATEST" == true ]]; then
        log WARN "Using latest commit (unreleased)"
    else
        local codename=$(echo "$install_json" | jq -r '.releases[0].codename')
        log INFO "Updating to release: $codename"
    fi

    # Update backends if client exists
    if [[ -d "$INSTALL_DIR/client" ]]; then
        log INFO "Updating client components..."
        update_backends "$install_json"
        download_files "client" "$install_json" "$commit"
        install_requirements "client" "$install_json"
        update_binaries "client" "$install_json" "$commit"
    fi

    # Update server if it exists
    if [[ -d "$INSTALL_DIR/server" ]]; then
        log INFO "Updating server components..."
        download_files "server" "$install_json" "$commit"
        install_requirements "server" "$install_json"
        update_binaries "server" "$install_json" "$commit"
    fi

    # Always update common components
    log INFO "Updating common components..."
    download_files "always" "$install_json" "$commit"
    install_requirements "always" "$install_json"
    update_binaries "always" "$install_json" "$commit"
}

# ============================================================================
# MAIN UPDATE FLOW
# ============================================================================

main() {
    mkdir -p "$TMP_DIR"

    echo "$BANNER"

    # Parse command line arguments
    parse_arguments "$@"

    # Pre-flight checks
    check_root_privileges
    
    log INFO "Full log transcript will be written to $LOG_FILE"
    
    validate_installation

    cd "$INSTALL_DIR"

    # Check for updates
    local latest_commit
    if ! latest_commit=$(check_for_updates); then
        cd "$START_PWD"
        exit 0
    fi

    # Fetch configuration and update
    local install_json=$(fetch_installation_config "$latest_commit")
    update_components "$install_json" "$latest_commit"

    # Save version and complete
    save_version_info "$latest_commit"

    log INFO "Update complete!"
    log INFO "Log file: $LOG_FILE"

    cd "$START_PWD"
    echo "Update completed, exiting !" # avoid blocking
    exit 0
}

main "$@"