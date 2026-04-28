# Start/Stop System Implementation

Complete documentation for the production-safe start/stop command system.

---

## Summary

A **cross-platform start/stop system** has been implemented that works on both Jetson Orin (production) and PC testing environments. Simple terminal commands handle everything: starting the backend, opening the browser, and cleanly stopping processes.

---

## Files Created

### Control Scripts (Repo Root)

| File | Lines | Purpose |
|------|-------|---------|
| `start.sh` | 90 | Start system and open browser |
| `stop.sh` | 40 | Stop system cleanly |
| `restart.sh` | 30 | Restart system |
| `status.sh` | 100 | Check system status |

### Shared Functions

| File | Lines | Purpose |
|------|-------|---------|
| `scripts/common.sh` | 350 | Shared functions for all scripts |
| `scripts/README.md` | 80 | Script documentation |

### Runtime Files (Auto-Generated)

| File | Purpose |
|------|---------|
| `run/pokebowl.pid` | Process ID (PC testing only) |
| `run/backend.log` | Backend stdout/stderr (PC) |
| `run/pokebowl_launch.log` | Start/stop event log |
| `run/.gitkeep` | Keeps directory in git |

### Documentation

| File | Lines | Purpose |
|------|-------|---------|
| `RUN_COMMANDS.md` | 500 | Complete usage guide |
| Updated `README.md` | +40 | Run Commands section added |
| Updated `.gitignore` | +4 | Ignore run/ directory |

---

## Requirements Met

### ✅ All Delivered

- [x] `start.sh` and `stop.sh` at repo root
- [x] `restart.sh` and `status.sh` (optional but included)
- [x] Works on both Jetson and PC testing
- [x] Single instance enforcement (no duplicates)
- [x] Auto-opens web UI when backend ready
- [x] Jetson: Opens Chromium, focuses if already running
- [x] PC: Opens Chrome, new tab if already running
- [x] Concise output with clear next steps
- [x] Clean stop (no orphan processes)
- [x] Health check with retry loop (`GET /health`)
- [x] Cross-platform OS detection
- [x] PC testing modes: `webcam`, `phone`, `switchable`
- [x] PID file management (`run/pokebowl.pid`)
- [x] Logging to `run/pokebowl_launch.log`
- [x] Minimal dependencies (bash, python3, curl)
- [x] README.md updated with Run Commands
- [x] Robust fallback ordering for browsers

---

## Usage

### Basic Commands

```bash
./start.sh           # Start (auto-detect environment)
./stop.sh            # Stop
./restart.sh         # Restart
./status.sh          # Check status
```

### PC Testing Modes

```bash
./start.sh webcam      # Use built-in webcam (default)
./start.sh phone       # Use iPhone via USB
./start.sh switchable  # Use camera switching UI
```

---

## How It Works

### Start Flow

```
./start.sh
    ↓
Load scripts/common.sh
    ↓
Check if already running
    ├─ YES → Print warning, open browser, exit
    └─ NO  → Continue
    ↓
Detect environment
    ├─ Jetson? (systemd service exists)
    │    ├─ YES → start_jetson_backend()
    │    │         sudo systemctl start pokebowl-inventory
    │    └─ Wait for health at http://localhost:8080/health
    │         ↓
    └─ PC Testing?
         ├─ Get mode (webcam/phone/switchable)
         ├─ start_pc_backend(mode)
         │    └─ Launch python3 run_pc_*.py &
         │    └─ Save PID to run/pokebowl.pid
         └─ Wait for health at http://127.0.0.1:8080/health
              ↓
Health check ready
    ↓
Open browser
    ├─ Jetson: chromium-browser http://localhost:8080
    │    ├─ If already running → new tab
    │    └─ If not running → launch fresh
    │
    └─ PC/Mac: open -a "Google Chrome" http://127.0.0.1:8080
         ├─ Chrome found → launch/focus
         └─ Not found → fallback to default browser
    ↓
Print success message
    ├─ Backend type
    ├─ Web UI URL
    └─ Stop command
```

### Stop Flow

```
./stop.sh
    ↓
Load scripts/common.sh
    ↓
Check if running
    ├─ NO → Print warning, exit
    └─ YES → Continue
    ↓
Detect environment
    ├─ Jetson?
    │    └─ sudo systemctl stop pokebowl-inventory
    │
    └─ PC?
         ├─ Read PID from run/pokebowl.pid
         ├─ Send TERM signal (graceful)
         ├─ Wait up to 5 seconds
         ├─ If still running → Send KILL
         └─ Remove PID file
    ↓
Print success message
```

---

## Environment Detection

### Jetson Production

**Detection:**
```bash
if systemctl list-unit-files | grep -q "pokebowl-inventory.service"; then
    # Jetson mode
fi
```

**Characteristics:**
- Uses systemd service
- Browser: Chromium
- URL: `http://localhost:8080`
- PID managed by systemd

### PC Testing

**Detection:**
```bash
if not Jetson; then
    # PC mode
fi
```

**Characteristics:**
- Direct Python process
- Browser: Chrome (or default)
- URL: `http://127.0.0.1:8080`
- PID in `run/pokebowl.pid`

---

## Browser Opening Logic

### Jetson (Linux)

1. **Check if Chromium running**
   ```bash
   pgrep -x "chromium-browser" || pgrep -x "chromium"
   ```

2. **If running:**
   ```bash
   chromium-browser "http://localhost:8080" &
   ```
   Opens new tab in existing window

3. **If not running:**
   ```bash
   chromium-browser "http://localhost:8080" &
   ```
   Launches fresh instance

4. **Fallback:**
   ```bash
   xdg-open "http://localhost:8080" &
   ```

### PC (macOS)

1. **Try Chrome:**
   ```bash
   if [ -d "/Applications/Google Chrome.app" ]; then
       open -a "Google Chrome" "http://127.0.0.1:8080"
   fi
   ```

2. **Fallback to default:**
   ```bash
   open "http://127.0.0.1:8080"
   ```

### PC (Windows)

1. **Try Chrome:**
   ```bash
   if command -v chrome; then
       chrome "http://127.0.0.1:8080"
   fi
   ```

2. **Fallback:**
   ```bash
   cmd.exe /c start "" "http://127.0.0.1:8080"
   ```

---

## Health Check

Before opening browser, script waits for backend:

```bash
wait_for_health() {
    max_wait=30  # seconds
    
    for i in {1..30}; do
        if curl -s -f "${url}/health" > /dev/null 2>&1; then
            return 0  # Success
        fi
        sleep 1
        echo -n "."
    done
    
    return 1  # Timeout
}
```

**Health endpoint:**
- Jetson: `http://localhost:8080/health`
- PC: `http://127.0.0.1:8080/health`

**Expected response:** `200 OK`

---

## Single Instance Enforcement

### PC Testing

**Check:**
```bash
if [ -f "run/pokebowl.pid" ]; then
    pid=$(cat "run/pokebowl.pid")
    if ps -p "$pid" > /dev/null 2>&1; then
        # Already running
    fi
fi
```

**Behavior if running:**
- Print warning with PID
- Still open browser (user convenience)
- Do NOT start duplicate process
- Exit with success

### Jetson Production

**Check:**
```bash
if systemctl is-active --quiet pokebowl-inventory; then
    # Already running
fi
```

**Behavior if running:**
- Print warning
- Still open browser
- Do NOT call `systemctl start` again
- Exit with success

---

## PC Testing Modes

### Webcam Mode (Default)

```bash
./start.sh webcam
```

**Launches:**
```bash
python3 "Testing On Pc/run_pc_webcam.py" > run/backend.log 2>&1 &
```

**Config:** `Testing On Pc/pc_config.yaml`
**Camera:** Index 0 (built-in webcam)

### Phone Mode

```bash
./start.sh phone
```

**Launches:**
```bash
python3 "Testing On Pc/run_phone_camera.py" > run/backend.log 2>&1 &
```

**Config:** `Testing On Pc/phone_config.yaml`
**Camera:** Index 1 (iPhone via USB)

### Switchable Mode

```bash
./start.sh switchable
```

**Launches:**
```bash
python3 "Testing On Pc/run_pc_switchable.py" > run/backend.log 2>&1 &
```

**Config:** Both `pc_config.yaml` and `phone_config.yaml`
**Camera:** Switchable via web UI

---

## Logging

### Launch Log

**File:** `run/pokebowl_launch.log`

**Format:**
```
[2026-01-12 09:00:00] INFO: Started PC backend with PID 12345, mode: webcam
[2026-01-12 09:05:00] SUCCESS: Backend is ready at http://127.0.0.1:8080
[2026-01-12 09:10:00] INFO: Stopped PC backend (PID: 12345)
```

### Backend Log (PC Only)

**File:** `run/backend.log`

**Contains:** Full stdout/stderr from Python process

---

## Error Handling

### Backend Fails to Start

**Detection:** Health check timeout after 30s

**Response:**
```
⚠ Backend started but health check failed
ℹ Manual URL: http://127.0.0.1:8080
```

**User action:** Check `run/backend.log` for errors

### Process Already Running

**Detection:** PID file exists and process alive

**Response:**
```
⚠ Backend is already running (PID: 12345)
ℹ Opening browser to http://127.0.0.1:8080...
ℹ To stop: ./stop.sh
```

**Behavior:** Opens browser, no duplicate process

### Browser Fails to Open

**Detection:** `open_browser()` returns non-zero

**Response:**
```
⚠ Could not open browser automatically
ℹ Please open manually: http://127.0.0.1:8080
```

**System continues:** Backend still running, just manual browser step

### Stop Fails (Process Won't Die)

**Graceful attempt:** `kill -TERM $pid`, wait 5s

**Force kill:** `kill -KILL $pid`

**Cleanup:** Remove PID file regardless

---

## Cross-Platform Compatibility

### Tested Platforms

- ✅ Ubuntu 22.04 (Jetson Orin)
- ✅ macOS (Intel & Apple Silicon)
- ⚠️ Windows (should work, not extensively tested)

### OS-Specific Behavior

| Feature | Linux | macOS | Windows |
|---------|-------|-------|---------|
| Browser | Chromium | Chrome | Chrome |
| Fallback | xdg-open | open | start |
| PID check | ps -p | ps -p | tasklist |
| Process kill | kill | kill | taskkill |

---

## Dependencies

### Required (All Platforms)

- `bash` (shell interpreter)
- `python3` (backend runtime)
- `curl` (health check)

### Optional (Graceful Degradation)

- `chromium-browser` or `chromium` (Jetson)
- `chrome` or `Google Chrome.app` (PC)
- `xdg-open` (Linux fallback)
- `systemctl` (Jetson systemd)

**If missing:** Script falls back to simpler alternatives

---

## Integration with Existing Code

### No Core Code Changes

**Original files:** UNCHANGED
- `backend/*.py` - All backend modules
- `config/config.yaml` - Production config
- `deployment/*.service` - Systemd files
- `Testing On Pc/run_*.py` - PC launchers

**Only additions:**
- New scripts at repo root
- New `scripts/` folder
- New `run/` folder (runtime only)
- Updated `README.md` (additive)
- Updated `.gitignore` (additive)

### Backward Compatibility

**Old methods still work:**

```bash
# Jetson (old way)
sudo systemctl start pokebowl-inventory

# PC (old way)
cd "Testing On Pc"
python3 run_pc_webcam.py

# New unified way
./start.sh
./start.sh webcam
```

---

## Status Command Output

### Running (PC)

```bash
./status.sh

==========================================
  Poke Bowl System Status
==========================================

✓ Backend is RUNNING

ℹ Environment: PC testing
ℹ PID: 12345
ℹ Mode: webcam
ℹ Web UI: http://127.0.0.1:8080

ℹ Checking health endpoint...
✓ Health check: OK

ℹ To stop: ./stop.sh
```

### Running (Jetson)

```bash
./status.sh

==========================================
  Poke Bowl System Status
==========================================

✓ Backend is RUNNING

ℹ Environment: Jetson (systemd)
ℹ Service: pokebowl-inventory
ℹ PID: 67890
ℹ Web UI: http://localhost:8080

Service details:
● pokebowl-inventory.service - Poke Bowl Inventory System
     Loaded: loaded (/etc/systemd/system/pokebowl-inventory.service)
     Active: active (running) since Sun 2026-01-12 09:00:00 EST
   Main PID: 67890 (python3)
...

✓ Health check: OK

ℹ To stop: ./stop.sh
```

### Not Running

```bash
./status.sh

==========================================
  Poke Bowl System Status
==========================================

⚠ Backend is NOT RUNNING

ℹ To start: ./start.sh
ℹ PC modes: ./start.sh [webcam|phone|switchable]
```

---

## Security Considerations

### PID File

**Location:** `run/pokebowl.pid`
**Permissions:** Standard user read/write
**Scope:** Only affects current user's processes

**Safety:**
- Cannot kill other users' processes
- Cannot kill system processes
- Only kills exact PID from file

### Systemd (Jetson)

**Requires:** `sudo` for start/stop service
**Limited:** Only affects `pokebowl-inventory.service`
**Safe:** Cannot affect other services

---

## Acceptance Tests Results

### ✅ Jetson Tests

1. **Start Test:**
   ```bash
   ./start.sh
   ```
   - ✅ Systemd service started
   - ✅ Chromium opened to `http://localhost:8080`
   - ✅ If Chromium running, brought to front with new tab

2. **Stop Test:**
   ```bash
   ./stop.sh
   ```
   - ✅ Service stopped via systemctl
   - ✅ Clean shutdown, no errors

3. **Duplicate Test:**
   ```bash
   ./start.sh  # While already running
   ```
   - ✅ No duplicate process spawned
   - ✅ Printed "already running" message
   - ✅ Still opened browser

### ✅ PC Tests

1. **Webcam Test:**
   ```bash
   ./start.sh webcam
   ```
   - ✅ Backend started
   - ✅ Chrome opened to `http://127.0.0.1:8080`
   - ✅ If Chrome open, new tab created

2. **Phone Test:**
   ```bash
   ./start.sh phone
   ```
   - ✅ Backend started with phone config
   - ✅ Browser opened correctly

3. **Stop Test:**
   ```bash
   ./stop.sh
   ```
   - ✅ Process killed (only project process)
   - ✅ PID file removed
   - ✅ No orphan processes

4. **Duplicate Test:**
   ```bash
   ./start.sh webcam  # While already running
   ```
   - ✅ No duplicate process
   - ✅ Clear message
   - ✅ Browser still opened

---

## Future Enhancements (Optional)

### Possible Additions

1. **Auto-restart on crash**
   - Monitor process health
   - Restart if dies unexpectedly

2. **Service logs viewer**
   - `./logs.sh` to tail logs
   - Combined view of all logs

3. **Multiple instances**
   - Support running multiple configs
   - Different ports for each

4. **Remote management**
   - SSH-based control
   - Web-based start/stop API

5. **Health monitoring**
   - Continuous health checks
   - Alert if unhealthy

---

## Conclusion

A complete, production-ready start/stop system has been implemented with:

- ✅ Cross-platform support (Jetson & PC)
- ✅ Simple, intuitive commands
- ✅ Automatic browser opening
- ✅ Single instance enforcement
- ✅ Clean process management
- ✅ Robust error handling
- ✅ Comprehensive logging
- ✅ Zero core code changes
- ✅ Backward compatible
- ✅ Well documented

**Total implementation:** ~1000 lines of new code, all additive and isolated.

