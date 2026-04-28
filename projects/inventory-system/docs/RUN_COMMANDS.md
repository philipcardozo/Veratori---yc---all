# Run Commands - Quick Reference

Complete guide for starting, stopping, and managing the Poke Bowl Inventory Vision System.

---

## Basic Commands

### Start the System

```bash
./start.sh
```

**What it does:**
- Detects environment (Jetson production or PC testing)
- Starts backend (systemd on Jetson, Python process on PC)
- Waits for health check
- Opens browser automatically to web UI
- **On Jetson**: Opens Chromium at `http://localhost:8080`
- **On PC**: Opens Chrome at `http://127.0.0.1:8080`

### Stop the System

```bash
./stop.sh
```

**What it does:**
- Gracefully stops backend
- Cleans up PID files
- **On Jetson**: Uses `systemctl stop`
- **On PC**: Sends TERM signal, then KILL if needed

### Restart the System

```bash
./restart.sh
```

Equivalent to `./stop.sh && ./start.sh` with proper timing.

### Check Status

```bash
./status.sh
```

**Shows:**
- Running state (running/stopped)
- Environment (Jetson/PC)
- Process ID
- Health check status
- Web UI URL

---

## PC Testing Modes

When running on PC, specify camera mode:

### Webcam Mode (Default)

```bash
./start.sh webcam
```

Uses built-in webcam (camera index 0).

### Phone Camera Mode

```bash
./start.sh phone
```

Uses iPhone via USB (camera index 1). 

**Requirements:**
- iPhone connected via USB
- iPhone unlocked and trusted

### Switchable Camera Mode

```bash
./start.sh switchable
```

Starts with camera switching UI - allows switching between webcam and phone in web interface.

---

## Examples

### Jetson Production

```bash
# Start production service
./start.sh

# Output:
# ✓ Backend service started
# ✓ Backend is ready at http://localhost:8080
# ✓ Opened in existing Chromium instance
# 
# System started successfully
# Backend: Jetson systemd service
# Web UI:  http://localhost:8080
# To stop: ./stop.sh
```

### PC Testing with Webcam

```bash
# Start with webcam
./start.sh webcam

# Output:
# ✓ Backend started (PID: 12345)
# ✓ Backend is ready at http://127.0.0.1:8080
# ℹ Opening browser to http://127.0.0.1:8080...
#
# System started successfully
# Backend: PC testing (webcam)
# Web UI:  http://127.0.0.1:8080
# To stop: ./stop.sh
```

### Check Status

```bash
./status.sh

# Output:
# ✓ Backend is RUNNING
#
# ℹ Environment: PC testing
# ℹ PID: 12345
# ℹ Mode: webcam
# ℹ Web UI: http://127.0.0.1:8080
#
# ℹ Checking health endpoint...
# ✓ Health check: OK
#
# ℹ To stop: ./stop.sh
```

---

## Behavior Details

### Already Running

If you run `./start.sh` while already running:

```bash
./start.sh

# Output:
# ⚠ Backend is already running (PID: 12345)
# ℹ Opening browser to http://127.0.0.1:8080...
# ℹ To stop: ./stop.sh
```

**Result**: No duplicate process, but browser opens/focuses on the URL.

### Browser Opening

**Jetson:**
- Tries to open in existing Chromium window (new tab)
- If Chromium not running, launches it fresh
- Falls back to `xdg-open` if Chromium not found

**macOS:**
- Opens in Google Chrome if available
- Falls back to system default browser
- Uses `open -a "Google Chrome" URL`

**Windows:**
- Opens in Chrome if available
- Falls back to default browser
- Uses `start chrome URL`

### Health Check

Before opening browser, script waits up to 30 seconds for:

```
GET /health -> 200 OK
```

If health check fails, browser still opens but with a warning.

---

## File Locations

### PID File
```
run/pokebowl.pid
```

Contains process ID of running backend (PC testing only).

### Launch Log
```
run/pokebowl_launch.log
```

Contains timestamped start/stop events.

### Backend Log (PC)
```
run/backend.log
```

Contains stdout/stderr from Python process.

---

## Troubleshooting

### "Backend is not running" but I just started it

**Check:**
1. Look at `run/backend.log` for errors
2. Verify camera is connected
3. Check Python dependencies installed
4. Run `./status.sh` for details

### Browser doesn't open

**Try:**
1. Open manually: `http://localhost:8080` (Jetson) or `http://127.0.0.1:8080` (PC)
2. Check if port 8080 is already in use: `lsof -i :8080`
3. Check health endpoint: `curl http://127.0.0.1:8080/health`

### "Failed to stop" error

**Solutions:**
- Check if process actually stopped: `./status.sh`
- Manually kill if needed: `kill $(cat run/pokebowl.pid)`
- On Jetson: `sudo systemctl status pokebowl-inventory`

### Phone camera mode fails

**Requirements:**
1. iPhone connected via USB
2. iPhone unlocked
3. Tapped "Trust This Computer"
4. Camera index correct in `Testing On Pc/phone_config.yaml`

**Test camera:**
```bash
cd "Testing On Pc"
python3 -c "import cv2; print('OK' if cv2.VideoCapture(1).isOpened() else 'FAIL')"
```

---

## Advanced Usage

### Custom Port

To change from default port 8080, edit:
- **Jetson**: `config/config.yaml`
- **PC**: `Testing On Pc/pc_config.yaml` or `phone_config.yaml`

Then update `scripts/common.sh`:
```bash
DEFAULT_PORT=8080  # Change this
```

### Silent Mode

Suppress browser opening (health check still runs):

```bash
export NO_BROWSER=1
./start.sh
```

### Custom Browser

Override default browser detection:

```bash
export BROWSER="firefox"
./start.sh
```

---

## Script Architecture

```
start.sh
  ↓
scripts/common.sh
  ↓
- detect_os()
- is_jetson()
- is_running()
  ↓
- start_jetson_backend() OR start_pc_backend()
  ↓
- wait_for_health()
  ↓
- open_browser()
```

**Key design principles:**
- Single instance enforcement (PID file)
- Graceful degradation (fallback browsers)
- Cross-platform compatibility
- Minimal dependencies
- Additive only (no core code changes)

---

## Integration with Existing Workflows

### Systemd (Jetson)

Scripts integrate with existing systemd service:

```bash
# These are equivalent on Jetson:
./start.sh
sudo systemctl start pokebowl-inventory

./stop.sh
sudo systemctl stop pokebowl-inventory
```

**Advantage of `./start.sh`:**
- Opens browser automatically
- Works on PC too
- Consistent interface

### Testing Scripts

Old PC testing scripts still work:

```bash
# Old way (still works):
cd "Testing On Pc"
python3 run_pc_webcam.py

# New way (recommended):
./start.sh webcam
```

---

## Production Deployment

### First Time Setup (Jetson)

```bash
# 1. Deploy code to Jetson
git clone <repo> && cd <repo>

# 2. Install systemd service (one time)
cd deployment
sudo bash install_service.sh

# 3. Use scripts from now on
cd ..
./start.sh
```

### Daily Operations

```bash
# Start system
./start.sh

# Check if running
./status.sh

# Restart after changes
./restart.sh

# Stop system
./stop.sh
```

---

## Quick Reference Card

```
┌─────────────────────────────────────────┐
│  POKE BOWL RUN COMMANDS                 │
├─────────────────────────────────────────┤
│  ./start.sh [mode]    Start system      │
│  ./stop.sh            Stop system       │
│  ./restart.sh [mode]  Restart system    │
│  ./status.sh          Check status      │
├─────────────────────────────────────────┤
│  PC MODES:                              │
│    webcam      Built-in camera          │
│    phone       iPhone via USB           │
│    switchable  Camera switching UI      │
├─────────────────────────────────────────┤
│  FILES:                                 │
│    run/pokebowl.pid        PID file     │
│    run/backend.log         Backend log  │
│    run/pokebowl_launch.log Launch log   │
└─────────────────────────────────────────┘
```

---

For more details, see main `README.md`.

