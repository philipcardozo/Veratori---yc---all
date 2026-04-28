#!/bin/bash
# Install systemd service for Veratori Inventory System
# Run with sudo: sudo bash install_service.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Veratori Inventory System Service Installation ===${NC}"
echo

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Error: Please run with sudo${NC}"
    exit 1
fi

# Get the actual user (not root)
ACTUAL_USER="${SUDO_USER:-$USER}"
ACTUAL_HOME=$(eval echo ~$ACTUAL_USER)

echo -e "${YELLOW}Installing for user: $ACTUAL_USER${NC}"
echo -e "${YELLOW}Home directory: $ACTUAL_HOME${NC}"
echo

# Get project directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo -e "${YELLOW}Project directory: $PROJECT_DIR${NC}"
echo

# Create service file with correct paths
SERVICE_FILE="/etc/systemd/system/veratori-inventory.service"

cat > "$SERVICE_FILE" << EOF
[Unit]
Description=Veratori Inventory System
After=network.target graphical.target
Wants=graphical.target

[Service]
Type=simple
User=$ACTUAL_USER
WorkingDirectory=$PROJECT_DIR
Environment="DISPLAY=:0"
Environment="XAUTHORITY=$ACTUAL_HOME/.Xauthority"

# Restart policy for production reliability
Restart=always
RestartSec=10

# Start the inventory system
ExecStart=/usr/bin/python3 $PROJECT_DIR/backend/main.py

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=veratori-inventory

# Resource limits (adjust based on requirements)
MemoryMax=2G
CPUQuota=400%

[Install]
WantedBy=multi-user.target
EOF

echo -e "${GREEN}✓ Service file created at $SERVICE_FILE${NC}"

# Reload systemd
echo -e "${YELLOW}Reloading systemd daemon...${NC}"
systemctl daemon-reload

# Enable service
echo -e "${YELLOW}Enabling service to start on boot...${NC}"
systemctl enable veratori-inventory.service

echo
echo -e "${GREEN}=== Installation Complete ===${NC}"
echo
echo "Service commands:"
echo "  Start:   sudo systemctl start veratori-inventory"
echo "  Stop:    sudo systemctl stop veratori-inventory"
echo "  Restart: sudo systemctl restart veratori-inventory"
echo "  Status:  sudo systemctl status veratori-inventory"
echo "  Logs:    sudo journalctl -u veratori-inventory -f"
echo
echo -e "${YELLOW}The service will start automatically on next boot.${NC}"
echo -e "${YELLOW}To start now: sudo systemctl start veratori-inventory${NC}"
echo

