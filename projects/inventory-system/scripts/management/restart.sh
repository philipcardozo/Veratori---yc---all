#!/bin/bash
# Restart Poke Bowl Inventory Vision System

set -e

# Load common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
source "$REPO_ROOT/scripts/common.sh"

# Main restart logic
main() {
    echo "=========================================="
    echo "  Restarting Poke Bowl System"
    echo "=========================================="
    echo ""
    
    # Stop if running
    if is_running; then
        print_info "Stopping current instance..."
        "$SCRIPT_DIR/stop.sh"
        echo ""
        sleep 2
    else
        print_info "No instance running, starting fresh..."
    fi
    
    # Start with provided arguments
    "$SCRIPT_DIR/start.sh" "$@"
}

# Run main
main "$@"





