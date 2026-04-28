#!/bin/bash
# Check status of Veratori Inventory Vision System

set -e

# Load common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/scripts/common.sh"

# Main status logic
main() {
    echo "=========================================="
    echo "  Veratori System Status"
    echo "=========================================="
    echo ""
    
    # Get status information
    local status_output=$(get_status)
    local state=$(echo "$status_output" | sed -n '1p')
    local env=$(echo "$status_output" | sed -n '2p')
    local pid=$(echo "$status_output" | sed -n '3p')
    
    if [ "$state" = "running" ]; then
        print_success "Backend is RUNNING"
        echo ""
        
        if [ "$env" = "jetson" ]; then
            print_info "Environment: Jetson (systemd)"
            print_info "Service: veratori-inventory"
            if [ -n "$pid" ]; then
                print_info "PID: $pid"
            fi
            print_info "Web UI: ${NETWORK_URL}"
            
            echo ""
            echo "Service details:"
            systemctl status veratori-inventory --no-pager -l | head -n 10
            
        else
            print_info "Environment: PC testing"
            if [ -n "$pid" ]; then
                print_info "PID: $pid"
                
                # Check which mode is running
                local cmdline=$(ps -p "$pid" -o command= 2>/dev/null)
                if echo "$cmdline" | grep -q "run_pc_webcam"; then
                    print_info "Mode: webcam"
                elif echo "$cmdline" | grep -q "run_phone_camera"; then
                    print_info "Mode: phone"
                elif echo "$cmdline" | grep -q "run_pc_switchable"; then
                    print_info "Mode: switchable"
                fi
            fi
            print_info "Web UI: ${LOCALHOST_URL}"
        fi
        
        # Check health endpoint
        echo ""
        print_info "Checking health endpoint..."
        if [ "$env" = "jetson" ]; then
            if curl -s -f "${NETWORK_URL}${HEALTH_ENDPOINT}" > /dev/null 2>&1; then
                print_success "Health check: OK"
            else
                print_warning "Health check: FAILED"
            fi
        else
            if curl -s -f "${LOCALHOST_URL}${HEALTH_ENDPOINT}" > /dev/null 2>&1; then
                print_success "Health check: OK"
            else
                print_warning "Health check: FAILED"
            fi
        fi
        
        echo ""
        print_info "To stop: ./stop.sh"
        
    else
        print_warning "Backend is NOT RUNNING"
        echo ""
        print_info "To start: ./start.sh"
        
        if [ "$env" = "pc" ]; then
            print_info "PC modes: ./start.sh [webcam|phone|switchable]"
        fi
    fi
    
    echo ""
}

# Run main
main "$@"





