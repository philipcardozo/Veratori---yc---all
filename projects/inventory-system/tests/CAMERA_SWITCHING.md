# Camera Source Switching for PC Testing

This enhancement adds the ability to switch between webcam and phone camera sources in real-time without restarting the application.

## New Files

- **`run_pc_switchable.py`**: Unified PC launcher with camera switching support
- **`pc_camera_switch.py`**: Camera switcher module for safe, atomic source switching
- **`CAMERA_SWITCHING.md`**: This documentation file

## Usage

### Starting the System

```bash
cd "Testing On Pc"
python3 run_pc_switchable.py
```

The system will start with the last-used camera source (defaults to webcam on first run).

### Switching Camera Sources

1. Open the web interface at **http://localhost:8080**
2. Look for the camera switcher buttons next to "Live Camera Feed"
3. Click **Webcam** or **Phone Camera** to switch sources
4. The video stream will pause briefly (~1-3 seconds) during the switch
5. Once complete, the video feed will resume from the new source

### Camera Source Buttons

- **Webcam**: Uses Camera 0 (built-in Mac webcam)
- **Phone Camera**: Uses Camera 1 (iPhone via USB or Continuity Camera)

The active source is highlighted in blue.

## Features

### Safe Switching

- **Atomic operation**: Camera switch is atomic - either succeeds completely or rolls back
- **Automatic rollback**: If the new source fails to open, the system automatically reverts to the previous working source
- **No crashes**: Clients remain connected during the switch; video resumes after transition
- **State persistence**: Last-used source is saved and restored on restart

### User Feedback

- Buttons are disabled during switch to prevent concurrent operations
- Visual feedback shows which source is active
- Error messages appear if a switch fails (e.g., phone not connected)
- Success messages confirm when switch completes

### Error Handling

If switching to phone camera fails:
- System automatically reverts to webcam
- Error message explains the issue
- Video stream continues from webcam without interruption

## Architecture

### Backend (Server-Side Switch)

The switch happens entirely on the backend:

1. **Stop streaming**: Pause the stream manager
2. **Release camera**: Close current cv2.VideoCapture
3. **Test new source**: Verify new camera is accessible
4. **Reinitialize**: Open new camera with updated configuration
5. **Restart streaming**: Resume stream manager with new source

If any step fails, the system rolls back to the previous source.

### Configuration

- **Webcam**: Uses `pc_config.yaml` (camera index 0)
- **Phone**: Uses `phone_config.yaml` (camera index 1)

Each configuration file contains camera settings, detector parameters, and streaming options.

### API Endpoints

#### GET `/api/camera/source`

Returns current camera source.

**Response:**
```json
{
  "active_source": "webcam"
}
```

#### POST `/api/camera/source`

Switches camera source.

**Request:**
```json
{
  "source": "webcam"
}
```

**Success Response:**
```json
{
  "ok": true,
  "active_source": "webcam",
  "restart_ms": 1523
}
```

**Error Response:**
```json
{
  "ok": false,
  "error": "Camera at index 1 is not accessible. Please check connection.",
  "active_source": "webcam"
}
```

## Compatibility

### Works With

- macOS (tested)
- Linux (should work)
- Windows (should work)

### Camera Requirements

- **Webcam**: Any OpenCV-compatible webcam at index 0
- **Phone**: 
  - iPhone via USB (requires Continuity Camera on macOS Ventura+)
  - Android via USB with appropriate drivers
  - Network cameras (configure in `phone_config.yaml`)

## Troubleshooting

### Phone Camera Not Detected

1. **iPhone not appearing**:
   - Connect iPhone via USB
   - Unlock and tap "Trust This Computer"
   - Enable Continuity Camera (Settings → General → AirPlay & Handoff)
   - Ensure both devices on same Apple ID

2. **Wrong camera index**:
   - Edit `phone_config.yaml`
   - Change `camera.index: 1` to `camera.index: 2` (or 3, etc.)
   - Restart application

3. **Test camera availability**:
   ```bash
   python3 -c "import cv2; [print(f'Camera {i}: {cv2.VideoCapture(i).isOpened()}') for i in range(5)]"
   ```

### Switch Fails Immediately

- Check camera permissions in System Preferences → Security & Privacy → Camera
- Verify camera is not in use by another application
- Check logs for detailed error messages

### Video Feed Freezes

- Wait 3-5 seconds for switch to complete
- Check browser console for errors
- Refresh page if needed (WebSocket will reconnect)

## Production vs Testing

### PC Testing Mode (This Implementation)

- **No authentication**: Auth disabled for easier testing
- **Camera switching**: Full source switching support
- **Location**: All code in `Testing On Pc/` folder

### Jetson Production Mode

- **Authentication**: Required (configured in backend)
- **Fixed camera**: Single USB camera, no switching
- **Location**: Original `backend/` code unchanged

**Important**: This camera switching feature is **only available in PC testing mode**. The Jetson production deployment continues to use a single fixed camera source.

## Performance

Switching between sources typically takes **1-3 seconds**:

- ~500ms to stop streaming and release camera
- ~300ms hardware reset delay
- ~500ms to open new camera
- ~200ms to restart streaming

Total: ~1500ms (varies by hardware)

## Development Notes

### Adding New Camera Sources

To add additional camera sources (e.g., external USB camera):

1. Create new config file in `Testing On Pc/` (e.g., `external_config.yaml`)
2. Update `pc_camera_switch.py` to recognize new source name
3. Add button to frontend UI
4. Update `get_config_for_source()` method

### Extending API

The camera switch API can be extended to support:
- Listing available cameras
- Testing camera without switching
- Adjusting camera settings (resolution, FPS) on the fly

## Testing Checklist

- [x] Start system with webcam
- [x] Switch to phone camera (with phone connected)
- [x] Switch back to webcam
- [x] Try switching to phone when unplugged (should rollback)
- [x] Verify WebSocket stays connected during switch
- [x] Check logs for errors
- [x] Confirm video resumes after each switch

## Logging

Camera switch operations are logged:

```
INFO - Switching camera source: webcam -> phone
INFO - Testing camera at index 1...
INFO - Stopping stream manager...
INFO - Releasing current camera...
INFO - Opening camera at index 1...
INFO - Camera opened successfully: USB Camera #1 (1280x720, 30fps)
INFO - Restarting stream manager...
INFO - Camera switch completed in 1523ms
```

## Future Enhancements

Potential improvements:
- Support for network cameras (RTSP streams)
- Multiple simultaneous camera views
- Camera settings adjustment UI
- Recording/snapshots from specific sources
- Picture-in-picture mode
