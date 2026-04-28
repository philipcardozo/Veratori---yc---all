# Camera Switching - Visual Guide

## 🎯 What You'll See

### Web Interface

```
┌─────────────────────────────────────────────────────────────────┐
│  Poke Bowl Inventory System - PC Testing        [Connected] 🟢  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  Live Camera Feed         [Webcam] [Phone Camera] Switched...   │
│ ┌───────────────────────────────────────────────────────────┐   │
│ │                                                           │   │
│ │                   🎥 VIDEO FEED                           │   │
│ │                                                           │   │
│ └───────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Button States

#### Before Switch (Webcam Active)
```
[Webcam]            Active: Blue background, white text
[Phone Camera]      Inactive: Transparent, blue text
```

#### During Switch
```
[Webcam]            Disabled: Faded
[Phone Camera]      Disabled: Faded
Status: "Switching to phone..."  (Orange text)
```

#### After Switch (Phone Active)
```
[Webcam]            Inactive: Transparent, blue text
[Phone Camera]      Active: Blue background, white text
Status: "Switched to phone (250ms)"  (Default text, auto-clears)
```

#### Error Case
```
[Webcam]            Active: Blue (stayed on webcam)
[Phone Camera]      Inactive: Transparent
Status: "Failed to open camera at index 1"  (Red text)
```

---

## 🔄 Switching Flow Diagram

```
┌──────────────┐
│   User       │
│ Clicks       │
│ Button       │
└──────┬───────┘
       │
       ▼
┌──────────────────────┐
│ Frontend JavaScript  │
│ POST /api/camera/    │
│      source          │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│ CameraSwitchManager                  │
│                                      │
│ 1. Lock (thread-safe)                │
│ 2. Stop streaming                    │
│ 3. Release current camera            │
│ 4. Load new config YAML              │
│ 5. Update camera settings            │
│ 6. Open new camera                   │
│    ├─ Success → Restart streaming    │
│    └─ Failure → Rollback             │
└──────┬───────────────────────────────┘
       │
       ▼
┌──────────────────────┐
│ Response to Frontend │
│ {ok, source, ms}     │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ UI Update            │
│ • Highlight button   │
│ • Show status        │
│ • Video continues    │
└──────────────────────┘
```

---

## 📁 File Structure

```
Testing On Pc/
│
├── 🚀 LAUNCHERS
│   ├── run_pc_switchable.py    ← NEW: Camera switching mode
│   ├── run_pc_webcam.py         ← Existing: Webcam only
│   └── run_phone_camera.py      ← Existing: Phone only
│
├── 🧠 CORE LOGIC
│   └── pc_camera_switch.py     ← NEW: Switch manager
│
├── 🎨 FRONTEND
│   └── index_switchable.html   ← NEW: UI with switch buttons
│
├── 🧪 TESTING
│   └── test_camera_switch.py   ← NEW: Automated tests
│
├── ⚙️ CONFIGURATION
│   ├── pc_config.yaml           ← Existing: Webcam config
│   ├── phone_config.yaml        ← Existing: Phone config
│   └── .camera_source_state     ← Auto-generated: State
│
└── 📚 DOCUMENTATION
    ├── QUICKSTART_SWITCHABLE.md
    ├── README_SWITCHABLE.md
    ├── CAMERA_SWITCH_IMPLEMENTATION.md
    ├── IMPLEMENTATION_SUMMARY.md
    ├── VISUAL_GUIDE.md
    └── COMMANDS.md (updated)
```

---

## 🎬 Usage Scenarios

### Scenario 1: Testing with Webcam

```bash
$ cd "Testing On Pc"
$ python3 run_pc_switchable.py

[OK] Camera: Webcam (index 0)
Web interface: http://localhost:8080

# Browser shows:
# [Webcam] active, video from built-in camera
```

### Scenario 2: Switch to Phone

```
User clicks [Phone Camera]
  ↓
Status: "Switching to phone..."
  ↓
2-5 seconds later...
  ↓
Status: "Switched to phone (300ms)"
  ↓
[Phone Camera] now active, video from iPhone
```

### Scenario 3: Phone Not Connected

```
User clicks [Phone Camera]
  ↓
Status: "Switching to phone..."
  ↓
2 seconds later...
  ↓
Status: "Failed to open camera at index 1"
  ↓
[Webcam] stays active (rollback successful)
```

### Scenario 4: Rapid Clicking

```
User clicks [Phone Camera]
User clicks [Phone Camera] again (too fast)
  ↓
First click: Processes
Second click: Ignored (already switching)
  ↓
Switch completes normally
```

---

## 🎨 Color Coding

### UI Elements

| Element | Active | Inactive | Disabled | Error |
|---------|--------|----------|----------|-------|
| Button Background | `#2196F3` (Blue) | Transparent | Same (faded) | - |
| Button Text | White | `#2196F3` | `#2196F3` | - |
| Status Normal | `#9aa0a6` | - | - | - |
| Status Switching | `#FF9800` (Orange) | - | - | - |
| Status Error | `#f44336` (Red) | - | - | - |

---

## 📊 Timeline Example

```
T=0ms    User clicks [Phone Camera]
         ├─ Buttons disabled
         └─ Status: "Switching to phone..."

T=50ms   Backend receives request
         └─ Acquires thread lock

T=100ms  Stops streaming
         └─ Clients wait for new frames

T=150ms  Releases webcam
         └─ Camera at index 0 closed

T=200ms  Loads phone_config.yaml
         └─ Camera index: 1

T=250ms  Opens phone camera
         ├─ SUCCESS: Camera at index 1 opened
         └─ Verifies frame read

T=300ms  Restarts streaming
         └─ Clients receive frames from phone

T=350ms  Response sent to frontend
         └─ {ok: true, source: "phone", restart_ms: 300}

T=400ms  UI updates
         ├─ [Phone Camera] highlighted
         ├─ Status: "Switched to phone (300ms)"
         └─ Video shows iPhone feed

T=3400ms Status message auto-cleared
         └─ Clean UI
```

---

## 🖼️ Screenshot Reference

### Initial State (Webcam)
```
┌────────────────────────────────────────────┐
│ Live Camera Feed    [Webcam*] [Phone]     │  * = Active
│ ┌──────────────────────────────────────┐   │
│ │  👤 Person visible from webcam       │   │
│ │  🌳 Room background                  │   │
│ └──────────────────────────────────────┘   │
└────────────────────────────────────────────┘
```

### After Switch (Phone)
```
┌────────────────────────────────────────────┐
│ Live Camera Feed    [Webcam] [Phone*]     │  * = Active
│ ┌──────────────────────────────────────┐   │
│ │  📦 Products from different angle    │   │
│ │  🔆 Better lighting from phone       │   │
│ └──────────────────────────────────────┘   │
└────────────────────────────────────────────┘
```

---

## 🔍 Debugging View

### Terminal Logs (Clean)

```
2026-01-12 08:00:00 - Camera switch requested: webcam -> phone
2026-01-12 08:00:00 - Switching camera source: webcam -> phone
2026-01-12 08:00:00 - Stopping stream manager...
2026-01-12 08:00:00 - Releasing camera at index 0...
2026-01-12 08:00:00 - Loading configuration for phone...
2026-01-12 08:00:00 - Updating camera to index 1...
2026-01-12 08:00:00 - Opening camera at index 1...
2026-01-12 08:00:00 - Verifying camera...
2026-01-12 08:00:00 - Restarting stream manager...
2026-01-12 08:00:00 - Camera switch successful: webcam -> phone (280ms)
```

### Browser Console (Success)

```javascript
Connecting to: ws://localhost:8080/ws
WebSocket connected
Switching camera to: phone
Response: {ok: true, active_source: "phone", restart_ms: 280}
Camera switched successfully
```

### Browser Console (Error)

```javascript
Connecting to: ws://localhost:8080/ws
WebSocket connected
Switching camera to: phone
Response: {ok: false, error: "Cannot open camera at index 1", active_source: "webcam"}
Camera switch failed, rolled back to: webcam
```

---

## ✅ Health Indicators

### System Healthy

- ✅ Button click → Status changes immediately
- ✅ Status shows timing (e.g., "250ms")
- ✅ Video resumes within 1-2 seconds
- ✅ No error messages
- ✅ WebSocket stays connected

### System Issues

- ⚠️ Status stuck on "Switching..."
- ⚠️ Error message doesn't clear
- ⚠️ Video feed shows "Reconnecting..."
- ⚠️ Buttons stay disabled

**Solution**: Check terminal logs for details

---

## 🎓 Quick Reference Card

```
┌────────────────────────────────────────────┐
│ CAMERA SWITCHING - QUICK REFERENCE         │
├────────────────────────────────────────────┤
│ START:  python3 run_pc_switchable.py      │
│ URL:    http://localhost:8080              │
│                                            │
│ BUTTONS:                                   │
│   [Webcam]       → Built-in camera (idx 0) │
│   [Phone Camera] → iPhone USB (idx 1)      │
│                                            │
│ STATUS:                                    │
│   Orange  → Switching in progress          │
│   Default → Success (with timing)          │
│   Red     → Error (with message)           │
│                                            │
│ TIMING:                                    │
│   Normal: 200-500ms                        │
│   Slow:   1-2 seconds                      │
│                                            │
│ TROUBLESHOOT:                              │
│   1. Check USB connection                  │
│   2. Trust iPhone                          │
│   3. Edit phone_config.yaml index          │
│   4. Check terminal logs                   │
└────────────────────────────────────────────┘
```

---

This visual guide helps you understand exactly what to expect when using the camera switching feature!





