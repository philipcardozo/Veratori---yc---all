#!/bin/bash
# Start Veratori Inventory Vision System
# Usage:
#   ./start.sh           - Start with default (Jetson: production, PC: webcam)
#   ./start.sh webcam    - Start PC testing with webcam
#   ./start.sh phone     - Start PC testing with phone camera
#   ./start.sh switchable - Start PC testing with switchable cameras

set -e

# Load common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
source "$REPO_ROOT/scripts/common.sh"

# Parse arguments
MODE="${1:-webcam}"  # Default to webcam for PC testing

# Main start logic
main() {
    echo "=========================================="
    echo "  Veratori Inventory Vision System"
    echo "=========================================="
    echo ""
    
    # Check if already running
    if is_running; then
        local pid=$(get_pid)
        print_warning "Backend is already running (PID: $pid)"
        
        # Still open browser to the URL
        if is_jetson; then
            wait_for_health "$NETWORK_URL" || true
            open_browser "$NETWORK_URL"
            echo ""
            print_info "To stop: ./stop.sh"
        else
            wait_for_health "$LOCALHOST_URL" || true
            open_browser "$LOCALHOST_URL"
            echo ""
            print_info "To stop: ./stop.sh"
        fi
        
        exit 0
    fi
    
    # Start backend based on environment
    if is_jetson; then
        # Jetson production mode
        print_info "Detected Jetson production environment"
        start_jetson_backend
        
        # Wait for health check
        if wait_for_health "$NETWORK_URL"; then
            open_browser "$NETWORK_URL"
        else
            print_warning "Backend started but health check failed"
            print_info "Manual URL: ${NETWORK_URL}"
        fi
        
        echo ""
        echo "=========================================="
        print_success "System started successfully"
        echo "=========================================="
        print_info "Backend: Jetson systemd service"
        print_info "Web UI:  ${NETWORK_URL}"
        print_info "To stop: ./stop.sh"
        
    else
        # PC testing mode
        print_info "Detected PC testing environment"
        print_info "Mode: $MODE"
        
        start_pc_backend "$MODE"
        
        # Wait for health check
        if wait_for_health "$LOCALHOST_URL"; then
            open_browser "$LOCALHOST_URL"
        else
            print_warning "Backend started but health check failed"
            print_info "Manual URL: ${LOCALHOST_URL}"
        fi
        
        echo ""
        echo "=========================================="
        print_success "System started successfully"
        echo "=========================================="
        print_info "Backend: PC testing ($MODE)"
        print_info "Web UI:  ${LOCALHOST_URL}"
        print_info "Logs:    $REPO_ROOT/run/backend.log"
        print_info "To stop: ./stop.sh"
    fi
    
    echo ""
}

# Run main
main "$@"





