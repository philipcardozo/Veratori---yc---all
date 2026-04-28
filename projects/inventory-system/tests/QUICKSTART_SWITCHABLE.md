# Camera Switching - Quick Start Guide

## Run with Camera Switching

```bash
cd "Testing On Pc"
python3 run_pc_switchable.py
```

Open browser: **http://localhost:8080**

## Switch Cameras

Look for the buttons next to "Live Camera Feed":

- Click **[Webcam]** to use your built-in camera
- Click **[Phone Camera]** to use your iPhone via USB

The active button will be highlighted in blue.

## Status Messages

- **"Switching to..."** - In progress
- **"Switched to ... (XXXms)"** - Success
- **Error message** - Failed (automatic rollback)

## Troubleshooting

### Phone Camera Not Working?

1. Connect iPhone via USB
2. Unlock iPhone
3. Tap "Trust This Computer"
4. Try clicking "Phone Camera" again

If still not working, edit `phone_config.yaml` and change camera index:
```yaml
camera:
  index: 2  # Try 2, 3, etc.
```

### Check Available Cameras

Run the script and look at the startup logs - it lists all detected cameras.

## Files

- **New launcher**: `run_pc_switchable.py`
- **Webcam config**: `pc_config.yaml` (index 0)
- **Phone config**: `phone_config.yaml` (index 1)
- **Full docs**: `README_SWITCHABLE.md`

## Old Launchers Still Work

- `python3 run_pc_webcam.py` - Webcam only (no switching)
- `python3 run_phone_camera.py` - Phone only (no switching)

## Test It

```bash
python3 test_camera_switch.py
```

This tests the API endpoints automatically.

## That's It!

Simple, fast, and safe camera switching for PC testing.





