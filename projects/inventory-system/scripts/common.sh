#!/bin/bash
# Common functions for Poke Bowl start/stop scripts

# Paths
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="$REPO_ROOT/run/pokebowl.pid"
LOG_FILE="$REPO_ROOT/run/pokebowl_launch.log"

# Default port and URLs
DEFAULT_PORT=8080
HEALTH_ENDPOINT="/health"
LOCALHOST_URL="http://127.0.0.1:${DEFAULT_PORT}"
NETWORK_URL="http://localhost:${DEFAULT_PORT}"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Log function
log() {
    local message="$1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $message" >> "$LOG_FILE"
}

# Print functions
print_success() {
    echo -e "${GREEN}✓${NC} $1"
    log "SUCCESS: $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
    log "WARNING: $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
    log "ERROR: $1"
}

print_info() {
    echo "ℹ $1"
    log "INFO: $1"
}

# Detect OS
detect_os() {
    case "$(uname -s)" in
        Linux*)     echo "linux" ;;
        Darwin*)    echo "macos" ;;
        MINGW*|MSYS*|CYGWIN*) echo "windows" ;;
        *)          echo "unknown" ;;
    esac
}

# Detect if running on Jetson (systemd service exists)
is_jetson() {
    if command -v systemctl &> /dev/null; then
        if systemctl list-unit-files | grep -q "pokebowl-inventory.service"; then
            return 0
        fi
    fi
    return 1
}

# Check if process is running
is_running() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0
        fi
    fi
    
    # Also check systemd on Jetson
    if is_jetson; then
        if systemctl is-active --quiet pokebowl-inventory; then
            return 0
        fi
    fi
    
    return 1
}

# Get current PID
get_pid() {
    if [ -f "$PID_FILE" ]; then
        cat "$PID_FILE"
    else
        echo ""
    fi
}

# Wait for health endpoint to be ready
wait_for_health() {
    local max_wait=30
    local wait_time=0
    local url="$1"
    
    print_info "Waiting for backend to be ready..."
    
    while [ $wait_time -lt $max_wait ]; do
        if curl -s -f "${url}${HEALTH_ENDPOINT}" > /dev/null 2>&1; then
            print_success "Backend is ready at ${url}"
            return 0
        fi
        sleep 1
        wait_time=$((wait_time + 1))
        echo -n "."
    done
    
    echo ""
    print_warning "Backend did not become ready within ${max_wait}s"
    return 1
}

# Open URL in browser
open_browser() {
    local url="$1"
    local os=$(detect_os)
    
    print_info "Opening browser to ${url}..."
    
    case "$os" in
        macos)
            # Try Chrome first, then default browser
            if [ -d "/Applications/Google Chrome.app" ]; then
                open -a "Google Chrome" "$url" 2>/dev/null && return 0
            fi
            open "$url" 2>/dev/null && return 0
            ;;
            
        linux)
            # On Jetson/Linux, try Chromium first
            if is_jetson; then
                # Try to bring existing Chromium to front
                if pgrep -x "chromium-browser" > /dev/null || pgrep -x "chromium" > /dev/null; then
                    # Chromium is running, open new tab
                    if command -v chromium-browser &> /dev/null; then
                        chromium-browser "$url" 2>/dev/null &
                    elif command -v chromium &> /dev/null; then
                        chromium "$url" 2>/dev/null &
                    fi
                    print_success "Opened in existing Chromium instance"
                    return 0
                else
                    # Launch Chromium fresh
                    if command -v chromium-browser &> /dev/null; then
                        chromium-browser "$url" 2>/dev/null &
                        print_success "Launched Chromium"
                        return 0
                    elif command -v chromium &> /dev/null; then
                        chromium "$url" 2>/dev/null &
                        print_success "Launched Chromium"
                        return 0
                    fi
                fi
            fi
            
            # Fallback to xdg-open
            if command -v xdg-open &> /dev/null; then
                xdg-open "$url" 2>/dev/null &
                return 0
            fi
            ;;
            
        windows)
            # Try Chrome first, then default
            if command -v chrome &> /dev/null; then
                chrome "$url" 2>/dev/null && return 0
            fi
            cmd.exe /c start "" "$url" 2>/dev/null && return 0
            ;;
    esac
    
    print_warning "Could not open browser automatically"
    print_info "Please open manually: ${url}"
    return 1
}

# Get launcher command based on mode
get_launcher_command() {
    local mode="$1"
    
    case "$mode" in
        webcam)
            echo "python3 \"$REPO_ROOT/tests/run_pc_webcam.py\""
            ;;
        phone)
            echo "python3 \"$REPO_ROOT/tests/run_phone_camera.py\""
            ;;
        switchable)
            echo "python3 \"$REPO_ROOT/tests/run_pc_switchable.py\""
            ;;
        *)
            # Default to webcam
            echo "python3 \"$REPO_ROOT/tests/run_pc_webcam.py\""
            ;;
    esac
}

# Start backend on PC
start_pc_backend() {
    local mode="$1"
    local launcher_cmd=$(get_launcher_command "$mode")
    
    print_info "Starting PC backend (mode: $mode)..."
    
    # Start in background and save PID
    eval "$launcher_cmd" > "$REPO_ROOT/run/backend.log" 2>&1 &
    local pid=$!
    
    echo "$pid" > "$PID_FILE"
    print_success "Backend started (PID: $pid)"
    log "Started PC backend with PID $pid, mode: $mode"
}

# Start backend on Jetson
start_jetson_backend() {
    print_info "Starting Jetson backend via systemd..."
    
    if sudo systemctl start pokebowl-inventory; then
        # Get PID from systemd
        local pid=$(systemctl show --property MainPID --value pokebowl-inventory)
        if [ "$pid" != "0" ] && [ -n "$pid" ]; then
            echo "$pid" > "$PID_FILE"
        fi
        print_success "Backend service started"
        log "Started Jetson backend via systemd"
        return 0
    else
        print_error "Failed to start systemd service"
        return 1
    fi
}

# Stop backend on PC
stop_pc_backend() {
    if [ ! -f "$PID_FILE" ]; then
        print_warning "No PID file found"
        return 1
    fi
    
    local pid=$(cat "$PID_FILE")
    
    if ! ps -p "$pid" > /dev/null 2>&1; then
        print_warning "Process $pid not running"
        rm -f "$PID_FILE"
        return 1
    fi
    
    print_info "Stopping backend (PID: $pid)..."
    
    # Try graceful shutdown first
    kill -TERM "$pid" 2>/dev/null
    
    # Wait up to 5 seconds for graceful shutdown
    for i in {1..5}; do
        if ! ps -p "$pid" > /dev/null 2>&1; then
            print_success "Backend stopped gracefully"
            rm -f "$PID_FILE"
            log "Stopped PC backend (PID: $pid)"
            return 0
        fi
        sleep 1
    done
    
    # Force kill if still running
    kill -KILL "$pid" 2>/dev/null
    print_success "Backend stopped (forced)"
    rm -f "$PID_FILE"
    log "Force-stopped PC backend (PID: $pid)"
    return 0
}

# Stop backend on Jetson
stop_jetson_backend() {
    print_info "Stopping Jetson backend via systemd..."
    
    if sudo systemctl stop pokebowl-inventory; then
        rm -f "$PID_FILE"
        print_success "Backend service stopped"
        log "Stopped Jetson backend via systemd"
        return 0
    else
        print_error "Failed to stop systemd service"
        return 1
    fi
}

# Get status
get_status() {
    if is_jetson; then
        # Jetson mode
        if systemctl is-active --quiet pokebowl-inventory; then
            local pid=$(systemctl show --property MainPID --value pokebowl-inventory)
            echo "running"
            echo "jetson"
            echo "$pid"
        else
            echo "stopped"
            echo "jetson"
            echo ""
        fi
    else
        # PC mode
        if is_running; then
            local pid=$(get_pid)
            echo "running"
            echo "pc"
            echo "$pid"
        else
            echo "stopped"
            echo "pc"
            echo ""
        fi
    fi
}





