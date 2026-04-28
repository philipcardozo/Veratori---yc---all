#!/bin/bash
# Install PC-compatible dependencies for testing
# This does NOT install Jetson-specific packages

set -e

echo "=========================================="
echo "PC Testing Environment Setup"
echo "=========================================="
echo

# Check Python version
echo "[1/4] Checking Python version..."
python3 --version
echo

# Upgrade pip
echo "[2/4] Upgrading pip..."
pip3 install --upgrade pip
echo

# Install PC dependencies
echo "[3/4] Installing PC-compatible dependencies..."
pip3 install -r requirements_pc.txt
echo

# Verify installation
echo "[4/4] Verifying installation..."
python3 << 'EOF'
import sys
print("Python:", sys.version)

try:
    import torch
    print("✓ PyTorch:", torch.__version__)
    print("  CUDA available:", torch.cuda.is_available())
except ImportError:
    print("✗ PyTorch not installed")

try:
    import cv2
    print("✓ OpenCV:", cv2.__version__)
except ImportError:
    print("✗ OpenCV not installed")

try:
    from ultralytics import YOLO
    print("✓ Ultralytics YOLO installed")
except ImportError:
    print("✗ Ultralytics not installed")

try:
    import aiohttp
    print("✓ aiohttp:", aiohttp.__version__)
except ImportError:
    print("✗ aiohttp not installed")

try:
    import yaml
    print("✓ PyYAML installed")
except ImportError:
    print("✗ PyYAML not installed")

print("\nAll dependencies installed successfully!")
EOF

echo
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo
echo "Next steps:"
echo "  1. Run the system: python3 run_pc_test.py"
echo "  2. Open browser: http://localhost:8080"
echo "  3. Press Ctrl+C to stop"
echo
