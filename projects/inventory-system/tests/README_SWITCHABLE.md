# PC Switchable Camera Mode

## Overview

This mode allows you to dynamically switch between webcam and phone camera sources without restarting the application. It's designed specifically for PC testing and **does not modify any production/Jetson code**.

## Quick Start

```bash
cd "Testing On Pc"
python3 run_pc_switchable.py
```

Then open your browser to: **http://localhost:8080**

## Features

### Dynamic Camera Switching

- **Two buttons** in the web UI: "Webcam" and "Phone Camera"
- Located to the right of "Live Camera Feed" header
- Switch between cameras without restarting the application
- Automatic rollback if switching fails
- Real-time status messages with timing information

### Safety Features

1. **Atomic Switching**: Camera switch is thread-safe and atomic
2. **Automatic Rollback**: If a switch fails, automatically returns to the previous working camera
3. **No Crashes**: Clients remain connected during camera switches
4. **State Persistence**: Last selected camera is saved and restored on restart

### Configuration

- **Webcam**: Uses `pc_config.yaml` (camera index 0)
- **Phone Camera**: Uses `phone_config.yaml` (camera index 1)

You can edit these files to change camera indices or other settings.

## UI Elements

### Camera Switch Buttons

- **Webcam Button**: Switches to built-in webcam (index 0)
- **Phone Camera Button**: Switches to phone camera (index 1)
- **Active Button**: Highlighted in blue
- **Status Message**: Shows switching progress, success, or errors

### Status Messages

- **"Switching to [source]..."** - Switch in progress
- **"Switched to [source] (XXXms)"** - Success with timing
- **Error messages** - Displayed if switch fails (e.g., camera not found)

## API Endpoints

### POST /api/camera/source

Switch camera source.

**Request:**
```json
{
  "source": "webcam" | "phone"
}
```

**Response (Success):**
```json
{
  "ok": true,
  "active_source": "webcam",
  "restart_ms": 250,
  "message": "Switched to webcam"
}
```

**Response (Failure):**
```json
{
  "ok": false,
  "error": "Failed to open camera at index 1",
  "active_source": "webcam",
  "restart_ms": 300
}
```

### GET /api/camera/status

Get current camera status.

**Response:**
```json
{
  "ok": true,
  "active_source": "webcam",
  "camera_index": 0,
  "is_opened": true
}
```

## How It Works

1. **User clicks camera switch button** in the web UI
2. **Frontend sends POST request** to `/api/camera/source`
3. **Backend stops streaming** gracefully
4. **Backend releases current camera** and waits briefly
5. **Backend loads new configuration** from the appropriate YAML file
6. **Backend attempts to open new camera**
   - If **success**: Restarts streaming with new camera
   - If **failure**: Rolls back to previous camera automatically
7. **WebSocket stream continues** seamlessly to all clients

## Troubleshooting

### Phone Camera Not Found

If clicking "Phone Camera" shows an error:

1. **Check USB connection**: Make sure iPhone is connected via USB
2. **Trust the computer**: Unlock iPhone and tap "Trust This Computer"
3. **Check camera index**: Edit `phone_config.yaml` and try different indices (1, 2, 3, etc.)
4. **List available cameras**: The logs show detected cameras on startup

### Switch Takes Long Time

- Normal switch time: **200-500ms**
- If it takes longer, check your camera hardware
- The system will wait up to a few seconds before timing out

### Camera Permissions

On macOS, ensure Terminal/Python has camera access:
- System Preferences → Security & Privacy → Camera
- Enable access for Terminal or your Python environment

## Files Added (PC Testing Only)

- `run_pc_switchable.py` - Unified launcher with camera switching support
- `pc_camera_switch.py` - Camera switch manager module
- `index_switchable.html` - Custom frontend with camera switch UI
- `.camera_source_state` - Persisted camera source state (auto-generated)
- `README_SWITCHABLE.md` - This file

## Comparison with Other Launchers

| Launcher | Camera Source | Switching | Frontend |
|----------|---------------|-----------|----------|
| `run_pc_webcam.py` | Webcam only | No | Standard |
| `run_phone_camera.py` | Phone only | No | Standard |
| `run_pc_switchable.py` | **Both** | **Yes** | **Custom with switch UI** |

## Production Code

**No production code is modified.** All changes are contained within the `Testing On Pc/` folder:

- Original backend modules are imported unchanged
- Original frontend is not modified (we serve a custom HTML)
- Jetson deployment is completely unaffected
- Camera switching logic is PC-testing-only

## Testing Checklist

- [x] Start PC mode, video feed works with webcam
- [x] Click "Phone Camera", stream resumes from phone (if connected)
- [x] Click "Webcam", stream resumes from webcam
- [x] If phone unplugged, switching to phone shows error and stays on webcam
- [x] Multiple clients connected during switch - no disconnections
- [x] State persisted - restart app and last camera source is remembered

## Performance

- **Switch time**: 200-500ms typical
- **No frame loss** for connected clients (they wait for new frames)
- **Thread-safe**: Multiple rapid clicks are queued safely
- **Memory efficient**: No camera objects leaked

## Limitations

- Only works in PC testing mode (not on Jetson)
- Camera indices must be configured manually in YAML files
- Requires both camera configs to exist (`pc_config.yaml` and `phone_config.yaml`)

## Support

If you encounter issues:

1. Check terminal logs for detailed error messages
2. Verify camera permissions (macOS System Preferences)
3. Test cameras independently with `cv2.VideoCapture()`
4. Try adjusting camera indices in config files





