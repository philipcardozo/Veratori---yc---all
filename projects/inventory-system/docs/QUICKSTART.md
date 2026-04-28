# Quick Start Guide

Get the Poke Bowl Inventory System running in **under 10 minutes** (after dependencies are installed).

---

## Super Quick Start (Already Configured Jetson)

If your Jetson already has JetPack 6.x and dependencies installed:

```bash
cd ~/Poke-Bowl---updated-January/backend
python3 main.py
```

Open browser: `http://localhost:8080`

Done!

---

## First-Time Setup (Fresh Jetson)

### Step 1: Clone Repository
```bash
cd ~
git clone <your-repo-url> Poke-Bowl---updated-January
cd Poke-Bowl---updated-January
```

### Step 2: Run Automated Setup
```bash
cd deployment
bash setup_jetson.sh
```

This script will:
- Update system packages
- Install system dependencies
- Install PyTorch (Jetson-optimized)
- Install Python packages
- Configure Jetson for max performance
- Test camera
- Verify all components

**Time**: ~15-30 minutes (depending on internet speed)

### Step 3: Test Manually
```bash
cd ~/Poke-Bowl---updated-January/backend
python3 main.py
```

You should see:
```
============================================================
Poke Bowl Inventory System
============================================================
Camera opened: 1280x720 @ 30fps
Model loaded in 2.34s
System ready!
Web interface available at: http://0.0.0.0:8080
============================================================
```

### Step 4: Access Web Interface

Open browser on any device on the same network:
```
http://<jetson-ip>:8080
```

To find your Jetson's IP:
```bash
hostname -I
```

### Step 5: Setup Auto-Start (Optional)
```bash
cd ~/Poke-Bowl---updated-January/deployment
sudo bash setup_autostart.sh
```

Reboot to test:
```bash
sudo reboot
```

After reboot, the system should automatically start and display on the HDMI monitor.

---

## Manual Installation (Step-by-Step)

If you prefer manual control:

### 1. System Dependencies
```bash
sudo apt-get update
sudo apt-get install -y python3-pip python3-dev libopencv-dev \
    python3-opencv v4l-utils chromium-browser
```

### 2. PyTorch (Jetson)
```bash
wget https://developer.download.nvidia.com/compute/redist/jp/v60/pytorch/torch-2.1.0a0+41361538.nv23.06-cp310-cp310-linux_aarch64.whl
pip3 install torch-2.1.0a0+41361538.nv23.06-cp310-cp310-linux_aarch64.whl
```

### 3. Torchvision
```bash
sudo apt-get install libjpeg-dev zlib1g-dev
git clone --branch v0.16.0 https://github.com/pytorch/vision torchvision
cd torchvision
python3 setup.py install --user
cd ..
```

### 4. Python Packages
```bash
cd ~/Poke-Bowl---updated-January
pip3 install -r requirements.txt
```

### 5. Verify Installation
```bash
cd deployment
bash quick_test.sh
```

---

## Configuration

### Quick Tweaks

Edit `config/config.yaml`:

**Change camera:**
```yaml
camera:
  index: 1  # Use /dev/video1 instead of /dev/video0
```

**Adjust detection sensitivity:**
```yaml
detector:
  conf_threshold: 0.3  # Higher = fewer false positives
```

**Change port:**
```yaml
server:
  port: 8080  # Change to any available port
```

**Reduce resource usage:**
```yaml
camera:
  width: 640
  height: 480

detector:
  imgsz: 416

stream:
  target_fps: 15
```

---

## Accessing from Different Devices

### Same Device
```
http://localhost:8080
```

### Same Network (LAN)
```
http://<jetson-ip>:8080
```

### HDMI Display (Auto-start)
After running `setup_autostart.sh`, Chromium will automatically open fullscreen on boot.

---

## Common Commands

### Start System
```bash
# Manually
cd ~/Poke-Bowl---updated-January/backend
python3 main.py

# As service
sudo systemctl start pokebowl-inventory
```

### Stop System
```bash
# Manual: Press Ctrl+C

# Service
sudo systemctl stop pokebowl-inventory
```

### View Logs
```bash
# Service logs
sudo journalctl -u pokebowl-inventory -f

# Application log
tail -f /tmp/pokebowl_inventory.log
```

### Check Status
```bash
sudo systemctl status pokebowl-inventory
```

### Restart System
```bash
sudo systemctl restart pokebowl-inventory
```

---

## Quick Troubleshooting

### Problem: Camera not found
```bash
# Check available cameras
v4l2-ctl --list-devices

# Update config.yaml with correct index
```

### Problem: CUDA out of memory
Edit `config/config.yaml`:
```yaml
detector:
  half: true      # Enable FP16
  imgsz: 416      # Reduce input size
```

### Problem: Low FPS
```yaml
camera:
  width: 640      # Lower resolution
  height: 480

stream:
  target_fps: 15  # Reduce target FPS
```

### Problem: Web interface not loading
```bash
# Check if service is running
sudo systemctl status pokebowl-inventory

# Check if port is accessible
curl http://localhost:8080

# Check firewall
sudo ufw allow 8080
```

### Problem: Service won't start
```bash
# View error logs
sudo journalctl -u pokebowl-inventory -n 50

# Check configuration
cd ~/Poke-Bowl---updated-January
python3 -c "import yaml; print(yaml.safe_load(open('config/config.yaml')))"

# Test manually
cd backend
python3 main.py
```

---

## Performance Tips

### Maximum Performance Mode
```bash
sudo nvpmodel -m 0
sudo jetson_clocks
```

### Monitor Resources
```bash
# GPU stats
tegrastats

# CPU/Memory
htop
```

### Optimize Configuration
```yaml
# Best performance (higher resource usage)
camera:
  width: 1280
  height: 720
detector:
  imgsz: 640
  half: true
stream:
  target_fps: 30

# Best efficiency (lower resource usage)
camera:
  width: 640
  height: 480
detector:
  imgsz: 416
  half: true
stream:
  target_fps: 15
```

---

## Next Steps

After getting the system running:

1. **Read the full README**: `README.md`
2. **Understand the architecture**: `ARCHITECTURE.md`
3. **Customize configuration**: `config/config.yaml`
4. **Setup auto-start**: `deployment/setup_autostart.sh`
5. **Monitor in production**: Use `journalctl` and web stats

---

## Getting Help

1. Check logs: `sudo journalctl -u pokebowl-inventory -f`
2. Run system test: `bash deployment/quick_test.sh`
3. Review README troubleshooting section
4. Check configuration: `config/config.yaml`

---

**That's it!** You should now have a fully functional real-time inventory system running on your Jetson.

