#!/bin/bash
# Quick system test script
# Run this to verify all components are working

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== Veratori Inventory System Test ===${NC}"
echo

# Get project directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Test 1: Check Python version
echo -e "${YELLOW}[1/7] Checking Python version...${NC}"
python3 --version
echo -e "${GREEN}✓ Python OK${NC}"
echo

# Test 2: Check dependencies
echo -e "${YELLOW}[2/7] Checking Python dependencies...${NC}"
python3 -c "import yaml; import cv2; import numpy; import aiohttp; print('All imports successful')"
echo -e "${GREEN}✓ Dependencies OK${NC}"
echo

# Test 3: Check YOLO model
echo -e "${YELLOW}[3/7] Checking YOLO model...${NC}"
if [ -f "models/best.pt" ]; then
    ls -lh models/best.pt
    echo -e "${GREEN}✓ Model found${NC}"
else
    echo -e "${RED}✗ Model not found: models/best.pt${NC}"
    exit 1
fi
echo

# Test 4: Check camera
echo -e "${YELLOW}[4/7] Checking camera devices...${NC}"
if command -v v4l2-ctl &> /dev/null; then
    v4l2-ctl --list-devices
    echo -e "${GREEN}✓ Camera devices listed${NC}"
else
    echo -e "${YELLOW}! v4l2-ctl not installed (optional)${NC}"
fi
echo

# Test 5: Check CUDA
echo -e "${YELLOW}[5/7] Checking CUDA availability...${NC}"
python3 << EOF
try:
    import torch
    if torch.cuda.is_available():
        print(f"CUDA available: {torch.cuda.get_device_name(0)}")
        print(f"CUDA version: {torch.version.cuda}")
    else:
        print("CUDA not available - will use CPU (slower)")
except ImportError:
    print("PyTorch not installed")
EOF
echo -e "${GREEN}✓ CUDA check complete${NC}"
echo

# Test 6: Test imports
echo -e "${YELLOW}[6/7] Testing backend imports...${NC}"
cd backend
python3 << EOF
try:
    from camera import USBCamera
    from detector import YOLODetector
    from inventory import InventoryTracker
    from server import VideoStreamServer
    print("✓ All backend modules import successfully")
except Exception as e:
    print(f"✗ Import error: {e}")
    exit(1)
EOF
cd ..
echo -e "${GREEN}✓ Backend modules OK${NC}"
echo

# Test 7: Validate config
echo -e "${YELLOW}[7/7] Validating configuration...${NC}"
if [ -f "config/config.yaml" ]; then
    python3 -c "import yaml; yaml.safe_load(open('config/config.yaml'))"
    echo -e "${GREEN}✓ Configuration valid${NC}"
else
    echo -e "${RED}✗ Configuration not found${NC}"
    exit 1
fi
echo

echo -e "${BLUE}=== Test Summary ===${NC}"
echo -e "${GREEN}All tests passed!${NC}"
echo
echo "To start the system manually:"
echo "  cd backend && python3 main.py"
echo
echo "To install as a service:"
echo "  cd deployment && sudo bash setup_autostart.sh"
echo

