#!/bin/bash
# Stop Poke Bowl Inventory Vision System

set -e

# Load common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
source "$REPO_ROOT/scripts/common.sh"

# Main stop logic
main() {
    echo "=========================================="
    echo "  Stopping Poke Bowl System"
    echo "=========================================="
    echo ""
    
    # Check if running
    if ! is_running; then
        print_warning "Backend is not running"
        exit 0
    fi
    
    # Stop based on environment
    if is_jetson; then
        print_info "Stopping Jetson production service..."
        stop_jetson_backend
    else
        print_info "Stopping PC testing backend..."
        stop_pc_backend
    fi
    
    echo ""
    echo "=========================================="
    print_success "System stopped successfully"
    echo "=========================================="
    print_info "To start: ./start.sh"
    echo ""
}

# Run main
main "$@"





