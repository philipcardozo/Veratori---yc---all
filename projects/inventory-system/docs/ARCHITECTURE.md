# System Architecture

## Overview

The Poke Bowl Inventory System is a production-ready edge AI application designed for continuous operation on NVIDIA Jetson Orin Nano. It provides real-time object detection and inventory tracking through a clean, modular architecture.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     Jetson Orin Nano                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐      ┌──────────────┐                    │
│  │   USB        │      │   HDMI       │                    │
│  │   Camera     │──────▶   Monitor    │                    │
│  └──────────────┘      └──────────────┘                    │
│         │                     ▲                             │
│         │                     │                             │
│         ▼                     │                             │
│  ┌─────────────────────────────────────────────┐           │
│  │         Backend Application                 │           │
│  │                                             │           │
│  │  ┌──────────┐    ┌──────────┐             │           │
│  │  │  Camera  │───▶│  YOLO    │             │           │
│  │  │  Handler │    │ Detector │             │           │
│  │  └──────────┘    └──────────┘             │           │
│  │                        │                   │           │
│  │                        ▼                   │           │
│  │                  ┌──────────┐             │           │
│  │                  │Inventory │             │           │
│  │                  │ Tracker  │             │           │
│  │                  └──────────┘             │           │
│  │                        │                   │           │
│  │                        ▼                   │           │
│  │  ┌─────────────────────────────────┐     │           │
│  │  │      Web Server + WebSockets    │     │           │
│  │  └─────────────────────────────────┘     │           │
│  └─────────────────┬───────────────────────┘           │
│                    │                                     │
└────────────────────┼─────────────────────────────────────┘
                     │
                     ▼
            ┌─────────────────┐
            │   Web Browser   │
            │   (Local/LAN)   │
            └─────────────────┘
```

---

## Component Design

### 1. Camera Handler (`camera.py`)

**Responsibility**: USB camera interface and frame capture

**Key Features**:
- V4L2 backend for Linux/Jetson compatibility
- Automatic reconnection on disconnect
- MJPEG encoding for USB bandwidth optimization
- Minimal latency (buffer size = 1)

**Interface**:
```python
class USBCamera:
    def open() -> bool
    def read() -> Tuple[bool, np.ndarray]
    def release()
    def reconnect() -> bool
    def get_info() -> dict
```

**Error Handling**:
- Graceful failure on disconnect
- Automatic retry with exponential backoff
- Returns last valid frame during reconnection

---

### 2. Object Detector (`detector.py`)

**Responsibility**: YOLO inference and detection management

**Key Features**:
- GPU-accelerated inference (CUDA)
- FP16 half-precision support for Jetson
- Configurable confidence and IoU thresholds
- Built-in warmup for consistent timing
- Performance metrics tracking

**Interface**:
```python
class YOLODetector:
    def load() -> bool
    def detect(frame) -> List[dict]
    def draw_detections(frame, detections) -> np.ndarray
    def get_fps() -> float
    def warmup(num_iterations)
```

**Optimization**:
- Model moved to GPU at startup
- Half-precision (FP16) reduces memory and increases speed
- Input preprocessing cached where possible

---

### 3. Inventory Tracker (`inventory.py`)

**Responsibility**: Count aggregation and temporal smoothing

**Key Features**:
- Configurable smoothing window (default: 10 frames)
- Multiple smoothing methods: median, mean, mode
- Per-class count tracking
- Confidence scoring based on variance

**Interface**:
```python
class InventoryTracker:
    def update(detections: List[dict])
    def get_inventory() -> Dict[str, int]
    def get_total_items() -> int
    def get_statistics() -> dict
```

**Algorithm**:
1. Count detections per class per frame
2. Maintain rolling window of N recent counts
3. Apply smoothing function (median by default)
4. Output stable inventory snapshot

**Why Temporal Smoothing?**:
- Reduces false positive/negative flicker
- Compensates for brief occlusions
- Provides stable counts for UI/reporting

---

### 4. Web Server (`server.py`)

**Responsibility**: HTTP server and WebSocket streaming

**Key Features**:
- Async I/O (aiohttp) for high concurrency
- WebSocket-based bidirectional communication
- JPEG encoding with configurable quality
- Base64 frame transmission
- Health check and stats endpoints

**Interface**:
```python
class VideoStreamServer:
    async def start()
    async def broadcast_frame(frame)
    async def broadcast_inventory(inventory)
    async def broadcast_stats(stats)
```

**Endpoints**:
- `GET /` - Main HTML interface
- `GET /ws` - WebSocket for streaming
- `GET /health` - Health check
- `GET /api/stats` - JSON statistics

**Protocol** (WebSocket):
```json
// Server → Client: Frame
{
  "type": "frame",
  "data": "<base64_jpeg>",
  "timestamp": 1234567890.123
}

// Server → Client: Inventory
{
  "type": "inventory",
  "data": {
    "Mango": 5,
    "Cantaloupe": 3
  },
  "timestamp": 1234567890.123
}

// Server → Client: Stats
{
  "type": "stats",
  "data": {
    "fps": 28.5,
    "inference_time": 0.035,
    "total_items": 8
  },
  "timestamp": 1234567890.123
}
```

---

### 5. Stream Manager (`server.py`)

**Responsibility**: Orchestrate streaming loop

**Key Features**:
- Async main loop
- FPS throttling
- Coordinated component lifecycle
- Error recovery

**Flow**:
```
1. Capture frame from camera
2. Run YOLO inference
3. Update inventory tracker
4. Draw detections on frame
5. Broadcast frame via WebSocket
6. Broadcast inventory update
7. Sleep to maintain target FPS
8. Repeat
```

---

### 6. Main Application (`main.py`)

**Responsibility**: System initialization and lifecycle

**Key Features**:
- Configuration loading (YAML)
- Component initialization sequence
- Signal handling (SIGINT, SIGTERM)
- Graceful shutdown
- Error logging

**Startup Sequence**:
1. Load configuration
2. Initialize camera
3. Load YOLO model
4. Warmup detector
5. Initialize inventory tracker
6. Start web server
7. Start streaming loop

**Shutdown Sequence**:
1. Stop streaming loop
2. Close all WebSocket connections
3. Release camera
4. Log final statistics

---

## Data Flow

### Frame Processing Pipeline

```
Camera → USB → V4L2 → OpenCV → numpy array (BGR)
                                    ↓
                              YOLO Inference (GPU)
                                    ↓
                              Detection List
                                    ↓
                         ┌──────────┴──────────┐
                         ▼                     ▼
                 Draw Detections        Update Inventory
                         │                     │
                         ▼                     ▼
                  Annotated Frame      Count Dictionary
                         │                     │
                         └──────────┬──────────┘
                                    ▼
                              WebSocket Broadcast
                                    ▼
                           Client Browser(s)
```

### Detection Object Structure

```python
{
    'class_id': int,           # 0-39
    'class_name': str,         # e.g., "Mango"
    'confidence': float,       # 0.0-1.0
    'bbox': [x1, y1, x2, y2]  # pixel coordinates
}
```

### Inventory Object Structure

```python
{
    "Mango": 5,          # class_name: count
    "Cantaloupe": 3,
    "Sprite": 12
}
```

---

## Performance Characteristics

### Latency Budget (per frame)

| Component          | Typical Time | Notes                    |
|--------------------|--------------|--------------------------|
| Camera capture     | ~5ms         | USB transfer             |
| YOLO inference     | 30-50ms      | FP16 on Jetson GPU       |
| Inventory update   | <1ms         | CPU operation            |
| Draw detections    | 2-5ms        | OpenCV operations        |
| JPEG encoding      | 3-8ms        | Quality-dependent        |
| WebSocket send     | 1-3ms        | Network dependent        |
| **Total**          | **~50ms**    | **~20 FPS achievable**   |

### Memory Usage

| Component          | Memory       |
|--------------------|--------------|
| YOLO model (FP16)  | ~20 MB       |
| Frame buffer       | ~2-3 MB      |
| History buffers    | ~1 MB        |
| Python runtime     | ~50-100 MB   |
| **Total**          | **~100 MB**  |

### GPU Utilization

- Inference: 30-50% (depends on model size)
- CUDA operations: Fully asynchronous
- Concurrent with CPU operations

---

## Configuration Management

All runtime configuration in `config/config.yaml`:

```yaml
camera:
  index: 0              # Device selection
  width: 1280           # Resolution
  height: 720
  fps: 30

detector:
  model_path: best.pt   # Model selection
  conf_threshold: 0.25  # Detection sensitivity
  iou_threshold: 0.45   # NMS aggressiveness
  imgsz: 640            # Input resolution
  device: '0'           # GPU selection
  half: true            # FP16 enable

inventory:
  smoothing_window: 10  # Temporal filter length
  smoothing_method: median

server:
  host: '0.0.0.0'       # Network binding
  port: 8080

stream:
  target_fps: 30        # Output throttling
```

**Design Principles**:
- Single source of truth
- No hardcoded constants in code
- Runtime reconfiguration (restart required)
- Validation on load

---

## Deployment Architecture

### Systemd Service Model

```
Boot
  ↓
systemd
  ↓
pokebowl-inventory.service
  ↓
python3 main.py
  ↓
[Running]
  │
  └─→ chromium-kiosk.service
        ↓
      Chromium Browser (fullscreen)
```

### Auto-Start Sequence

1. **System Boot**: Jetson powers on
2. **Network Ready**: `network.target` reached
3. **Backend Start**: `pokebowl-inventory.service` starts
4. **Server Ready**: Web server listening on port 8080
5. **Display Start**: `chromium-kiosk.service` starts
6. **Browser Launch**: Chromium opens fullscreen to localhost:8080
7. **WebSocket Connect**: Browser establishes WebSocket
8. **Streaming Active**: Video and inventory updates flowing

### Recovery Behavior

| Failure Mode          | Detection           | Recovery Action           |
|-----------------------|---------------------|---------------------------|
| Camera disconnect     | Read failure        | Reconnect loop (5 attempts)|
| YOLO inference error  | Exception           | Log and continue          |
| WebSocket disconnect  | Connection close    | Client auto-reconnect     |
| Service crash         | systemd monitor     | Auto-restart (10s delay)  |
| GPU OOM               | CUDA exception      | Fail with log             |

---

## Security Considerations

### Current Implementation

- **No authentication**: Suitable for isolated networks only
- **No encryption**: HTTP/WebSocket unencrypted
- **Bind all interfaces**: `0.0.0.0` allows LAN access

### Production Hardening (Not Implemented)

- Add authentication middleware
- Use HTTPS/WSS with certificates
- Restrict binding to localhost or specific IPs
- Implement rate limiting
- Add input validation on WebSocket messages

---

## Testing Strategy

### Unit Testing (Not Included)

Each module is independently testable:
- `camera.py`: Mock cv2.VideoCapture
- `detector.py`: Test with dummy frames
- `inventory.py`: Test with synthetic detections
- `server.py`: Test with aiohttp test client

### Integration Testing

Use `deployment/quick_test.sh`:
1. Verify dependencies
2. Test imports
3. Check hardware availability
4. Validate configuration

### System Testing

Manual testing procedure:
1. Start system: `python3 main.py`
2. Verify web interface loads
3. Check video stream displays
4. Verify inventory updates
5. Test camera disconnect/reconnect
6. Monitor logs for errors

---

## Monitoring and Observability

### Logs

- **systemd journal**: `journalctl -u pokebowl-inventory -f`
- **Application log**: `/tmp/pokebowl_inventory.log`
- **Log levels**: INFO, WARNING, ERROR

### Metrics (Real-time)

- FPS (inference and display)
- Inference time (ms)
- Frame count
- Active WebSocket connections
- Total items in inventory

### Health Check

`GET /health` returns:
```json
{
  "status": "healthy",
  "uptime_seconds": 12345,
  "active_connections": 2,
  "frames_streamed": 54321
}
```

---

## Scalability Considerations

### Current Limitations

- Single camera input
- Single YOLO model
- Local web server only
- No persistent storage
- No historical data

### Potential Enhancements

1. **Multi-camera support**: Parallel StreamManager instances
2. **Model switching**: Runtime model reload
3. **Data persistence**: SQLite inventory history
4. **Cloud integration**: MQTT/REST API reporting
5. **Analytics**: Historical trends, alerts
6. **Multi-device**: Distributed deployment

---

## Technology Stack

| Layer             | Technology         | Version    |
|-------------------|--------------------|------------|
| Hardware          | Jetson Orin Nano   | -          |
| OS                | Ubuntu             | 22.04      |
| CUDA              | CUDA Toolkit       | 11.x       |
| Python            | Python             | 3.10       |
| DL Framework      | PyTorch            | 2.1.0      |
| Vision Library    | OpenCV             | 4.8+       |
| Object Detection  | Ultralytics YOLO   | 8.0+       |
| Web Framework     | aiohttp            | 3.9+       |
| Config Format     | YAML               | -          |
| Process Manager   | systemd            | -          |
| Browser           | Chromium           | Latest     |

---

## Future Improvements

### Short-term
- [ ] Add configuration hot-reload
- [ ] Implement HTTP authentication
- [ ] Add CSV export for inventory
- [ ] Create web-based configuration editor

### Medium-term
- [ ] Multi-camera support
- [ ] Historical data tracking
- [ ] Alerting system (email/SMS)
- [ ] REST API for external integration

### Long-term
- [ ] Cloud dashboard
- [ ] Mobile app
- [ ] AI-powered analytics
- [ ] Multi-site deployment management

---

## References

- YOLO: https://github.com/ultralytics/ultralytics
- Jetson Documentation: https://developer.nvidia.com/embedded/jetson
- aiohttp: https://docs.aiohttp.org/
- systemd: https://systemd.io/

---

**Document Version**: 1.0  
**Last Updated**: January 2026

