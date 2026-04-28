#!/bin/bash
# Complete Jetson setup script - installs everything from scratch
# Run on a fresh JetPack 6.x installation

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Veratori Inventory System${NC}"
echo -e "${BLUE}Complete Jetson Orin Nano Setup${NC}"
echo -e "${BLUE}========================================${NC}"
echo

# Check if running on Jetson
if [ ! -f /etc/nv_tegra_release ]; then
    echo -e "${YELLOW}Warning: Not running on a Jetson device${NC}"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Get project directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo -e "${YELLOW}Project directory: $PROJECT_DIR${NC}"
echo

# Update system
echo -e "${BLUE}[1/8] Updating system packages...${NC}"
sudo apt-get update
sudo apt-get upgrade -y
echo -e "${GREEN}✓ System updated${NC}"
echo

# Install system dependencies
echo -e "${BLUE}[2/8] Installing system dependencies...${NC}"
sudo apt-get install -y \
    python3-pip \
    python3-dev \
    libopencv-dev \
    python3-opencv \
    v4l-utils \
    chromium-browser \
    gstreamer1.0-tools \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    libjpeg-dev \
    zlib1g-dev \
    git \
    curl \
    wget

echo -e "${GREEN}✓ System dependencies installed${NC}"
echo

# Install PyTorch
echo -e "${BLUE}[3/8] Installing PyTorch for Jetson...${NC}"

TORCH_WHEEL="torch-2.1.0a0+41361538.nv23.06-cp310-cp310-linux_aarch64.whl"
TORCH_URL="https://developer.download.nvidia.com/compute/redist/jp/v60/pytorch/$TORCH_WHEEL"

if python3 -c "import torch" 2>/dev/null; then
    echo -e "${YELLOW}PyTorch already installed${NC}"
else
    cd /tmp
    if [ ! -f "$TORCH_WHEEL" ]; then
        echo "Downloading PyTorch wheel..."
        wget "$TORCH_URL"
    fi
    pip3 install "$TORCH_WHEEL"
    echo -e "${GREEN}✓ PyTorch installed${NC}"
fi
echo

# Install Torchvision
echo -e "${BLUE}[4/8] Installing Torchvision...${NC}"

if python3 -c "import torchvision" 2>/dev/null; then
    echo -e "${YELLOW}Torchvision already installed${NC}"
else
    cd /tmp
    if [ ! -d "torchvision" ]; then
        git clone --branch v0.16.0 https://github.com/pytorch/vision torchvision
    fi
    cd torchvision
    python3 setup.py install --user
    echo -e "${GREEN}✓ Torchvision installed${NC}"
fi
echo

# Install Python dependencies
echo -e "${BLUE}[5/8] Installing Python dependencies...${NC}"
cd "$PROJECT_DIR"
pip3 install -r requirements.txt
echo -e "${GREEN}✓ Python dependencies installed${NC}"
echo

# Set Jetson to max performance
echo -e "${BLUE}[6/8] Configuring Jetson performance...${NC}"
if command -v nvpmodel &> /dev/null; then
    sudo nvpmodel -m 0
    sudo jetson_clocks
    echo -e "${GREEN}✓ Performance mode set to maximum${NC}"
else
    echo -e "${YELLOW}! nvpmodel not found (skip on non-Jetson)${NC}"
fi
echo

# Test camera
echo -e "${BLUE}[7/8] Testing camera...${NC}"
if ls /dev/video* 1> /dev/null 2>&1; then
    echo "Available cameras:"
    v4l2-ctl --list-devices
    echo -e "${GREEN}✓ Camera(s) detected${NC}"
else
    echo -e "${YELLOW}! No cameras detected - please connect USB camera${NC}"
fi
echo

# Test system
echo -e "${BLUE}[8/8] Running system tests...${NC}"
cd "$PROJECT_DIR/deployment"
bash quick_test.sh
echo

# Summary
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Setup Complete!${NC}"
echo -e "${BLUE}========================================${NC}"
echo
echo "Next steps:"
echo
echo "1. Test the system manually:"
echo "   cd $PROJECT_DIR/backend"
echo "   python3 main.py"
echo
echo "2. Access the web interface:"
echo "   http://$(hostname -I | awk '{print $1}'):8080"
echo
echo "3. Setup auto-start on boot:"
echo "   cd $PROJECT_DIR/deployment"
echo "   sudo bash setup_autostart.sh"
echo
echo "4. Reboot to test auto-start:"
echo "   sudo reboot"
echo

