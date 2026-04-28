#!/bin/bash
# Setup auto-start for Veratori Inventory System with browser kiosk mode
# This script configures both the backend service and Chromium kiosk display

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== Veratori Inventory Auto-Start Setup ===${NC}"
echo

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Error: Please run with sudo${NC}"
    exit 1
fi

ACTUAL_USER="${SUDO_USER:-$USER}"
ACTUAL_HOME=$(eval echo ~$ACTUAL_USER)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo -e "${YELLOW}User: $ACTUAL_USER${NC}"
echo -e "${YELLOW}Project: $PROJECT_DIR${NC}"
echo

# Install backend service
echo -e "${YELLOW}[1/3] Installing backend service...${NC}"

cat > /etc/systemd/system/veratori-inventory.service << EOF
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

Restart=always
RestartSec=10

ExecStart=/usr/bin/python3 $PROJECT_DIR/backend/main.py

StandardOutput=journal
StandardError=journal
SyslogIdentifier=veratori-inventory

MemoryMax=2G
CPUQuota=400%

[Install]
WantedBy=multi-user.target
EOF

echo -e "${GREEN}✓ Backend service created${NC}"

# Install Chromium kiosk service
echo -e "${YELLOW}[2/3] Installing Chromium kiosk service...${NC}"

cat > /etc/systemd/system/chromium-kiosk.service << EOF
[Unit]
Description=Chromium Kiosk Mode for Veratori Inventory
After=veratori-inventory.service graphical.target
Wants=graphical.target
Requires=veratori-inventory.service

[Service]
Type=simple
User=$ACTUAL_USER
Environment="DISPLAY=:0"
Environment="XAUTHORITY=$ACTUAL_HOME/.Xauthority"

ExecStartPre=/bin/sleep 8

ExecStart=/usr/bin/chromium-browser \
    --kiosk \
    --noerrdialogs \
    --disable-infobars \
    --disable-session-crashed-bubble \
    --disable-features=TranslateUI \
    --no-first-run \
    --disable-suggestions-service \
    --disable-save-password-bubble \
    --start-fullscreen \
    http://localhost:8080

Restart=always
RestartSec=10

[Install]
WantedBy=graphical.target
EOF

echo -e "${GREEN}✓ Chromium kiosk service created${NC}"

# Enable services
echo -e "${YELLOW}[3/3] Enabling services...${NC}"

systemctl daemon-reload
systemctl enable veratori-inventory.service
systemctl enable chromium-kiosk.service

echo -e "${GREEN}✓ Services enabled${NC}"

echo
echo -e "${GREEN}=== Setup Complete ===${NC}"
echo
echo "The system will now auto-start on boot with the following sequence:"
echo "  1. Backend inventory system starts"
echo "  2. Chromium opens in fullscreen kiosk mode"
echo
echo "Commands:"
echo "  Start all:    sudo systemctl start veratori-inventory chromium-kiosk"
echo "  Stop all:     sudo systemctl stop chromium-kiosk veratori-inventory"
echo "  Backend logs: sudo journalctl -u veratori-inventory -f"
echo "  Status:       sudo systemctl status veratori-inventory"
echo
echo -e "${YELLOW}Reboot to test auto-start: sudo reboot${NC}"
echo

