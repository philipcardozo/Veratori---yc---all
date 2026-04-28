# Complete Project Breakdown: Poke Bowl Inventory Vision System

## Table of Contents
1. [System Overview](#system-overview)
2. [Architecture Components](#architecture-components)
3. [Startup Flow](#startup-flow)
4. [Runtime Processing Pipeline](#runtime-processing-pipeline)
5. [Data Flow](#data-flow)
6. [Component Details](#component-details)
7. [Database Schema](#database-schema)
8. [Web Interface](#web-interface)
9. [Authentication Flow](#authentication-flow)
10. [Deployment & Operations](#deployment--operations)

---

## System Overview

**Purpose**: Real-time computer vision inventory tracking system for restaurant environments using YOLO object detection on NVIDIA Jetson Orin Nano.

**Key Capabilities**:
- Real-time object detection (40 product classes)
- Temporal smoothing for stable counts
- Persistent inventory tracking with SQLite
- Product freshness monitoring (5-day expiration)
- Automatic sales detection and attribution
- Low stock and expiration alerts
- Email notifications via SMTP
- Secure web-based dashboard
- Session-based authentication

**Performance**:
- 15-30 FPS processing
- 30-50ms inference time per frame
- <100ms end-to-end latency
- ~40% CPU, ~35% GPU usage

---

## Architecture Components

### 1. **Backend Modules** (`backend/`)

#### `main.py` - Application Entry Point
- **Role**: Orchestrates all components, manages lifecycle
- **Key Functions**:
  - Loads configuration from `config/config.yaml`
  - Initializes all components in sequence
  - Manages graceful shutdown
  - Creates PID file for single-instance protection

#### `camera.py` - USB Camera Handler
- **Class**: `USBCamera`
- **Responsibilities**:
  - Opens V4L2 camera device (`/dev/video0`)
  - Captures frames at configured resolution (1280x720 @ 30fps)
  - Handles camera disconnection/reconnection
  - Uses MJPEG format for better USB bandwidth
  - Maintains buffer size of 1 for low latency

#### `detector.py` - YOLO Inference Engine
- **Class**: `YOLODetector`
- **Responsibilities**:
  - Loads YOLO model (`best.pt`) with CUDA acceleration
  - Runs inference on frames (FP16 precision)
  - Applies confidence (0.25) and IoU (0.45) thresholds
  - Draws bounding boxes and labels on frames
  - Tracks inference time and FPS statistics

#### `inventory.py` - Base Inventory Tracker
- **Class**: `InventoryTracker`
- **Responsibilities**:
  - Counts detections per class per frame
  - Applies temporal smoothing (median/mean/mode over 10 frames)
  - Reduces noise from detection fluctuations
  - Provides smoothed inventory counts

#### `inventory_persistent.py` - Enhanced Inventory Tracker
- **Class**: `PersistentInventoryTracker` (extends `InventoryTracker`)
- **Additional Features**:
  - Saves inventory snapshots to database every 5 seconds
  - Tracks product freshness (first seen, expiration status)
  - Integrates sales attribution engine
  - Integrates alert engine
  - Restores state from database on startup

#### `persistence.py` - Database Layer
- **Class**: `PersistenceManager`
- **Responsibilities**:
  - SQLite database management (WAL mode for concurrency)
  - Stores inventory snapshots
  - Tracks product freshness
  - Logs sales events
  - Logs alerts
  - Automatic cleanup of old data (30-day retention)

#### `sales_attribution.py` - Sales Detection Engine
- **Class**: `SalesAttributionEngine`
- **Responsibilities**:
  - Compares consecutive inventory snapshots
  - Detects inventory decreases (sales)
  - Validates sales with temporal confirmation (2 intervals)
  - Applies cooldown (10 seconds) to prevent duplicate sales
  - Attributes sales to specific products (SKU-level)

#### `alerts.py` - Alert System
- **Class**: `AlertEngine`
- **Responsibilities**:
  - Monitors low stock conditions (configurable thresholds)
  - Monitors product expiration (5+ days old)
  - Validates alerts with temporal confirmation
  - Applies cooldown (1 hour) to prevent spam
  - Sends email notifications via SMTP
  - Logs alerts to database

#### `auth.py` - Authentication Module
- **Class**: `AuthManager`, `SessionManager`
- **Responsibilities**:
  - Bcrypt password hashing
  - HMAC-signed session tokens
  - 24-hour session TTL
  - Session verification

#### `server.py` - Web Server & Streaming
- **Classes**: `VideoStreamServer`, `StreamManager`
- **Responsibilities**:
  - Serves frontend HTML files
  - WebSocket connections for real-time streaming
  - Broadcasts frames (JPEG encoded, base64)
  - Broadcasts inventory updates
  - Broadcasts freshness, sales, alerts data
  - REST API endpoints (`/api/stats`, `/api/sales`, etc.)
  - Authentication middleware for protected routes

### 2. **Frontend** (`frontend/`)

#### `index.html` - Main Dashboard
- **Features**:
  - Live video feed with detection overlays
  - Real-time inventory display (sorted by count)
  - Product freshness tracking (6 products)
  - Sales log (automatic, EST timestamps)
  - Alerts panel
  - Diagnostics panel (FPS, inference time, etc.)
  - WebSocket client for real-time updates

#### `login.html` - Authentication Page
- **Features**:
  - Username/password form
  - Session cookie management
  - Redirects to dashboard on success

### 3. **Configuration** (`config/`)

#### `config.yaml` - System Configuration
- Camera settings (index, resolution, FPS)
- Detector settings (model path, thresholds, device)
- Inventory settings (smoothing, persistence, expiration)
- Alert thresholds (per-product low stock limits)
- Server settings (host, port)
- Stream settings (target FPS)

### 4. **Deployment** (`deployment/`)

#### Systemd Services
- `pokebowl-inventory.service` - Backend service
- `chromium-kiosk.service` - Browser kiosk mode
- `install_service.sh` - Service installation script
- `setup_autostart.sh` - Auto-start configuration

### 5. **Scripts** (`scripts/`)

#### `common.sh` - Shared Functions
- Environment detection (Jetson vs PC)
- Process management (start/stop/status)
- Health check waiting
- Browser opening

---

## Startup Flow

### Step 1: User Initiates Startup
```bash
./start.sh
```

### Step 2: Script Detection (`start.sh` + `scripts/common.sh`)
1. **Detects Environment**:
   - Checks if running on Jetson (systemd service exists)
   - Falls back to PC mode if not Jetson

2. **Checks if Already Running**:
   - Reads PID file (`run/pokebowl.pid`)
   - Checks process status
   - If running, opens browser and exits

### Step 3: Backend Initialization

#### Jetson Mode:
- Starts systemd service: `sudo systemctl start pokebowl-inventory`
- Service runs: `python3 backend/main.py`

#### PC Mode:
- Starts Python process directly: `python3 Testing\ On\ Pc/run_pc_webcam.py`
- Saves PID to `run/pokebowl.pid`

### Step 4: Application Bootstrap (`main.py`)

1. **Create PID File**:
   - Checks for existing PID file
   - Validates process is not already running
   - Creates new PID file

2. **Load Configuration**:
   - Reads `config/config.yaml`
   - Falls back to defaults if file missing

3. **Initialize Components** (in order):

   **a) Camera (`USBCamera`)**:
   - Opens V4L2 device (`/dev/video0` or configured index)
   - Sets resolution (1280x720)
   - Sets FPS (30)
   - Configures MJPEG format
   - Sets buffer size to 1

   **b) Detector (`YOLODetector`)**:
   - Loads YOLO model (`best.pt`)
   - Moves model to CUDA device
   - Enables FP16 precision (Jetson optimization)
   - Extracts class names from model
   - Warms up model (5 dummy inferences)

   **c) Inventory Tracker (`PersistentInventoryTracker`)**:
   - Initializes base tracker with smoothing (10 frames, median)
   - Initializes persistence manager (SQLite database)
   - **Restores state from database**:
     - Loads latest inventory snapshot
     - Restores freshness tracking data
   - Initializes sales attribution engine
   - Initializes alert engine

   **d) Web Server (`VideoStreamServer`)**:
   - Loads authentication configuration (environment variables)
   - Sets up HTTP routes:
     - `/` - Main dashboard (protected)
     - `/login` - Login page (public)
     - `/api/login` - Login endpoint (public)
     - `/ws` - WebSocket (protected)
     - `/api/stats`, `/api/sales`, etc. (protected)
   - Initializes WebSocket connection set

   **e) Stream Manager (`StreamManager`)**:
   - Coordinates camera, detector, inventory, and server
   - Sets target FPS (30)

4. **Start Web Server**:
   - Starts aiohttp server on configured host/port (0.0.0.0:8080)
   - Logs server URL

5. **Start Streaming Loop**:
   - Launches async streaming task
   - Begins frame capture → detection → inventory → broadcast cycle

### Step 5: Browser Launch
- Script waits for health endpoint (`/health`)
- Opens browser to `http://localhost:8080` (Jetson) or `http://127.0.0.1:8080` (PC)

---

## Runtime Processing Pipeline

### Main Loop (`StreamManager.stream_loop()`)

**Frequency**: Runs continuously, targeting 30 FPS (33ms per frame)

#### Frame Capture Phase
1. **Read Frame** (`camera.read()`):
   - Captures frame from USB camera
   - Returns BGR numpy array (H, W, 3)
   - If capture fails, attempts reconnection

#### Detection Phase
2. **Run YOLO Inference** (`detector.detect(frame)`):
   - Resizes frame to model input size (640x640)
   - Runs inference on GPU (CUDA)
   - Applies confidence threshold (0.25)
   - Applies NMS with IoU threshold (0.45)
   - Returns list of detections:
     ```python
     {
         'class_id': int,
         'class_name': str,
         'confidence': float,
         'bbox': [x1, y1, x2, y2]
     }
     ```

#### Inventory Update Phase
3. **Update Inventory** (`inventory_tracker.update(detections)`):
   - Counts detections per class in current frame
   - Adds counts to history buffer (deque, maxlen=10)
   - Computes smoothed inventory:
     - **Median smoothing**: Takes median of last 10 frame counts
     - Reduces noise from detection fluctuations
   - Updates current inventory snapshot

4. **Persistence Operations** (every 5 seconds):
   - **Save Snapshot** (`persistence.save_inventory_snapshot()`):
     - Saves current inventory to database
     - Includes timestamp, frame number, total items
   
   - **Update Freshness** (`persistence.update_product_freshness()`):
     - For each product in inventory:
       - If first time seen: records `first_seen_utc`
       - Updates `last_seen_utc`
       - Calculates age in days
       - Marks as expired if age > 5 days
   
   - **Detect Sales** (`sales_attribution.process_snapshot()`):
     - Compares current inventory with previous snapshot
     - Detects decreases (potential sales)
     - Validates with temporal confirmation (2 intervals)
     - Checks cooldown (10 seconds)
     - Logs validated sales to database
   
   - **Evaluate Alerts** (`alert_engine.evaluate()`):
     - Checks low stock conditions (count ≤ threshold)
     - Checks expiration conditions (age > 5 days)
     - Validates with temporal confirmation (2 intervals)
     - Checks cooldown (1 hour)
     - Sends email notifications
     - Logs alerts to database

#### Visualization Phase
5. **Draw Detections** (`detector.draw_detections(frame, detections)`):
   - Draws bounding boxes (green rectangles)
   - Draws labels with class name and confidence
   - Returns annotated frame

#### Broadcasting Phase
6. **Broadcast Frame** (`server.broadcast_frame(annotated_frame)`):
   - Encodes frame as JPEG (quality 85)
   - Converts to base64 string
   - Sends to all connected WebSocket clients:
     ```json
     {
         "type": "frame",
         "data": "<base64_jpeg>",
         "timestamp": 1234567890.123
     }
     ```

7. **Broadcast Inventory** (`server.broadcast_inventory(inventory)`):
   - Sends current inventory to all clients:
     ```json
     {
         "type": "inventory",
         "data": {"mango": 5, "watermelon": 3, ...},
         "timestamp": 1234567890.123
     }
     ```

8. **Broadcast Stats** (every 1 second):
   - Sends performance metrics:
     ```json
     {
         "type": "stats",
         "data": {
             "fps": 25.5,
             "inference_time": 0.035,
             "total_items": 42,
             "frame_count": 1500,
             "active_connections": 2
         }
     }
     ```

9. **Broadcast Freshness** (every 1 second):
   - Sends freshness data:
     ```json
     {
         "type": "freshness",
         "data": {
             "mango": {
                 "age_days": 2.5,
                 "is_expired": false
             },
             ...
         }
     }
     ```

10. **Broadcast Sales** (every 1 second):
    - Sends recent sales log:
      ```json
      {
          "type": "sales",
          "data": [
              {
                  "timestamp_est": "2026-01-15 02:30:45 PM EST",
                  "product_name": "mango",
                  "quantity_delta": 1,
                  "inventory_before": 6,
                  "inventory_after": 5
              },
              ...
          ]
      }
      ```

11. **Broadcast Alerts** (every 1 second):
    - Sends recent alerts:
      ```json
      {
          "type": "alerts",
          "data": [
              {
                  "alert_type": "low_stock",
                  "product_name": "mango",
                  "severity": "warning",
                  "message": "Low stock alert: mango count is 2 (threshold: 3)",
                  "timestamp_est": "2026-01-15 02:35:00 PM EST"
              },
              ...
          ]
      }
      ```

#### FPS Control
12. **Maintain Target FPS**:
    - Calculates elapsed time for loop iteration
    - Sleeps if loop completed faster than frame interval (33ms)
    - Ensures consistent frame rate

---

## Data Flow

### Frame Flow
```
USB Camera → OpenCV Capture → BGR Frame (numpy array)
    ↓
YOLO Detector → GPU Inference → Detections List
    ↓
Inventory Tracker → Count & Smooth → Smoothed Inventory
    ↓
Detector → Draw Boxes → Annotated Frame
    ↓
Server → JPEG Encode → Base64 → WebSocket → Browser
```

### Inventory Flow
```
Detections → Count per Class → History Buffer (10 frames)
    ↓
Median Smoothing → Current Inventory
    ↓
Every 5 seconds:
    ├─→ Database Snapshot
    ├─→ Freshness Update
    ├─→ Sales Detection
    └─→ Alert Evaluation
```

### Sales Detection Flow
```
Current Snapshot → Compare with Previous → Detect Decrease
    ↓
Add to Pending Decreases → Validate (2 intervals) → Check Cooldown (10s)
    ↓
Validated Sale → Log to Database → Broadcast to Clients
```

### Alert Flow
```
Inventory + Freshness State → Check Conditions
    ↓
Low Stock? → Validate (2 intervals) → Check Cooldown (1h)
Expiration? → Validate (2 intervals) → Check Cooldown (1h)
    ↓
Validated Alert → Send Email → Log to Database → Broadcast to Clients
```

---

## Component Details

### Camera Module (`camera.py`)

**Key Features**:
- V4L2 backend for Linux/Jetson
- Automatic reconnection on disconnect
- MJPEG format for USB efficiency
- Buffer size of 1 for low latency
- Last frame caching for display during reconnection

**Reconnection Logic**:
- Detects failed frame read
- Releases camera
- Retries up to 5 times with 2-second delays
- Logs reconnection status

### Detector Module (`detector.py`)

**Model Loading**:
- Uses Ultralytics YOLO
- Loads `best.pt` (40 classes)
- Moves to CUDA device
- Enables FP16 precision (Jetson optimization)
- Warms up with 5 dummy inferences

**Inference**:
- Input size: 640x640 (configurable)
- Confidence threshold: 0.25
- IoU threshold: 0.45 (NMS)
- Returns detections with bounding boxes

**Performance Tracking**:
- Maintains last 100 inference times
- Calculates average FPS
- Provides statistics via `get_info()`

### Inventory Tracker (`inventory.py`)

**Smoothing Methods**:
1. **Median** (default): Most robust to outliers
2. **Mean**: Smooth averaging
3. **Mode**: Most common value

**History Buffer**:
- Per-class deque with maxlen=10
- Stores count per frame
- Automatically maintains sliding window

**Inventory Output**:
- Only includes non-zero counts
- Maps class IDs to names
- Provides sorted views (by count or name)

### Persistent Inventory Tracker (`inventory_persistent.py`)

**State Restoration**:
- On startup, loads latest inventory snapshot
- Restores freshness tracking state
- Continues tracking from previous session

**Snapshot Interval**:
- Default: 5 seconds
- Configurable in `config.yaml`
- Balances database size vs. temporal resolution

**Freshness Tracking**:
- Tracks 6 products: passion fruit, maui custard, lemon cake, mango, watermelon, pineapple
- Records `first_seen_utc` on first detection
- Updates `last_seen_utc` on each detection
- Calculates age in days
- Marks expired if age > 5 days

### Sales Attribution Engine (`sales_attribution.py`)

**Detection Algorithm**:
1. Compare current snapshot with previous
2. Detect decreases (delta < 0)
3. Add to pending decreases
4. Validate with temporal confirmation (2 intervals)
5. Check cooldown (10 seconds)
6. Log validated sale

**Temporal Validation**:
- Requires decrease to persist for 2 consecutive intervals
- Prevents false positives from detection noise
- Clears pending if count increases

**Cooldown**:
- Prevents duplicate sales for same product
- Default: 10 seconds
- Tracks last sale time per product

### Alert Engine (`alerts.py`)

**Low Stock Alerts**:
- Configurable thresholds per product
- Default thresholds:
  - mango: 3
  - watermelon: 2
  - pineapple: 2
  - passion fruit: 2
  - maui custard: 2
  - lemon cake: 2
- Validates with 2-interval confirmation
- Cooldown: 1 hour

**Expiration Alerts**:
- Triggers when product age > 5 days
- Validates with 2-interval confirmation
- Cooldown: 1 hour

**Email Notifications**:
- Configured via environment variables:
  - `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`
  - `NOTIFY_TO`, `NOTIFY_FROM`
- Sends HTML and plain text emails
- Graceful degradation if SMTP unavailable

### Persistence Manager (`persistence.py`)

**Database Schema**:
- `inventory_snapshots`: Timestamped inventory states
- `product_freshness`: First seen, last seen, expiration status
- `sales_log`: Validated sales events with EST timestamps
- `alerts_log`: Alert events with metadata

**WAL Mode**:
- Write-Ahead Logging for better concurrency
- Allows concurrent reads during writes
- Better crash recovery

**Data Retention**:
- Automatic cleanup of data older than 30 days
- Runs on startup
- Keeps last 100 snapshots and alerts regardless of age

### Authentication (`auth.py`)

**Password Hashing**:
- Bcrypt with 12 rounds
- Secure password storage

**Session Management**:
- HMAC-signed tokens
- Contains: username, issued_at, expires_at
- 24-hour TTL (configurable)
- HttpOnly cookies (prevents XSS)

**Configuration**:
- Environment variables:
  - `AUTH_ENABLED`: Enable/disable (default: true)
  - `AUTH_SESSION_SECRET`: Secret for HMAC signing
  - `AUTH_SESSION_TTL`: Session lifetime in seconds
  - `AUTH_USERS_JSON`: JSON mapping usernames to bcrypt hashes

### Web Server (`server.py`)

**Routes**:
- `GET /` - Main dashboard (protected)
- `GET /login` - Login page (public)
- `POST /api/login` - Login endpoint (public)
- `POST /api/logout` - Logout endpoint
- `GET /health` - Health check (public)
- `GET /ws` - WebSocket connection (protected)
- `GET /api/stats` - Statistics (protected)
- `GET /api/sales` - Sales log (protected)
- `GET /api/alerts` - Alerts log (protected)
- `GET /api/freshness` - Freshness data (protected)

**WebSocket Protocol**:
- Client connects → Server sends initial data (inventory, freshness, sales, alerts)
- Server broadcasts updates as they occur
- Client can send `ping` → Server responds with `pong`
- Client can request frame with `request_frame`

**Frame Encoding**:
- JPEG compression (quality 85)
- Base64 encoding for JSON transport
- ~50-100KB per frame (1280x720)

---

## Database Schema

### `inventory_snapshots`
```sql
CREATE TABLE inventory_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp_utc REAL NOT NULL,
    frame_number INTEGER NOT NULL,
    total_items INTEGER NOT NULL,
    inventory_json TEXT NOT NULL,  -- JSON: {"product": count, ...}
    created_at REAL NOT NULL
);
```

### `product_freshness`
```sql
CREATE TABLE product_freshness (
    product_name TEXT PRIMARY KEY,
    first_seen_utc REAL NOT NULL,
    last_seen_utc REAL NOT NULL,
    is_expired BOOLEAN DEFAULT 0,
    expiration_days INTEGER DEFAULT 5,
    updated_at REAL NOT NULL
);
```

### `sales_log`
```sql
CREATE TABLE sales_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp_utc REAL NOT NULL,
    timestamp_est TEXT NOT NULL,  -- Formatted: "2026-01-15 02:30:45 PM EST"
    product_name TEXT NOT NULL,
    quantity_delta INTEGER NOT NULL,
    inventory_before INTEGER,
    inventory_after INTEGER,
    created_at REAL NOT NULL
);
```

### `alerts_log`
```sql
CREATE TABLE alerts_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp_utc REAL NOT NULL,
    timestamp_est TEXT NOT NULL,
    alert_type TEXT NOT NULL,  -- "low_stock" or "expiration"
    product_name TEXT NOT NULL,
    severity TEXT NOT NULL,  -- "info", "warning", "critical"
    message TEXT NOT NULL,
    metadata_json TEXT,  -- JSON with additional data
    acknowledged BOOLEAN DEFAULT 0,
    created_at REAL NOT NULL
);
```

**Indexes**:
- `idx_inventory_timestamp` on `inventory_snapshots(timestamp_utc DESC)`
- `idx_sales_timestamp` on `sales_log(timestamp_utc DESC)`
- `idx_sales_product` on `sales_log(product_name, timestamp_utc DESC)`
- `idx_alerts_timestamp` on `alerts_log(timestamp_utc DESC)`
- `idx_alerts_product_type` on `alerts_log(product_name, alert_type, timestamp_utc DESC)`

---

## Web Interface

### Dashboard Layout (`index.html`)

**Header**:
- Title: "Poke Bowl Inventory System"
- Connection status indicator (green dot when connected)
- Diagnostics button (hidden panel)
- Logout button

**Main Content** (2-column layout):

**Left Column - Video Feed**:
- Live video stream with detection overlays
- Bounding boxes and labels
- Auto-reconnects on disconnect

**Right Column - Data Panels**:

1. **Inventory Display**:
   - Product counts sorted by quantity (highest first)
   - Total items summary
   - Updates in real-time

2. **Freshness Tracking**:
   - Shows 6 tracked products
   - Displays age in days
   - Visual indicators:
     - Gray: Fresh (< 5 days)
     - Red: Expired (≥ 5 days)
   - Format: "Fresh - X days old" or "EXPIRED (X days old)"

3. **Sales Log**:
   - Automatic sales detection
   - EST timestamps
   - Product name and quantity
   - Chronological order (newest first)
   - Shows last 100 sales

4. **Alerts Panel**:
   - Low stock alerts
   - Expiration alerts
   - Severity indicators
   - Timestamps

**Diagnostics Panel** (hidden, hover to show):
- FPS (frames per second)
- Inference time (ms)
- Total frames processed
- Active WebSocket connections
- Total items in inventory

### WebSocket Client (`index.html` JavaScript)

**Connection**:
```javascript
const ws = new WebSocket('ws://localhost:8080/ws');
```

**Message Handling**:
- `frame`: Updates video feed (base64 JPEG → `<img>`)
- `inventory`: Updates inventory display
- `freshness`: Updates freshness panel
- `sales`: Updates sales log
- `alerts`: Updates alerts panel
- `stats`: Updates diagnostics panel

**Reconnection Logic**:
- Detects disconnect
- Attempts reconnection with exponential backoff
- Shows connection status indicator

---

## Authentication Flow

### Login Process

1. **User visits `/`**:
   - Server checks for session cookie (`pb_session`)
   - If no cookie or invalid → Redirects to `/login`

2. **User submits credentials** (`/api/login`):
   - Server receives username and password
   - `AuthManager.authenticate()`:
     - Looks up username in `AUTH_USERS_JSON`
     - Verifies password with bcrypt
     - Creates session token (HMAC-signed)
   - Server sets HttpOnly cookie:
     ```
     Set-Cookie: pb_session=<token>; HttpOnly; SameSite=Lax; Max-Age=86400
     ```
   - Returns JSON: `{"success": true}`

3. **User redirected to `/`**:
   - Server verifies session cookie
   - Extracts username from token
   - Serves dashboard

### Session Verification

**On Each Request**:
1. Extract `pb_session` cookie
2. `SessionManager.verify_session(token)`:
   - Splits token into payload and signature
   - Verifies HMAC signature
   - Checks expiration (`expires_at`)
   - Returns username if valid
3. If valid → Allow access
4. If invalid → Redirect to `/login`

### WebSocket Authentication

**Connection Request**:
- Client connects to `/ws`
- Server checks session cookie
- If valid → Accept connection
- If invalid → Send error and close:
  ```json
  {"error": "Unauthorized", "type": "error"}
  ```

### Logout

**Process**:
1. User clicks logout button
2. Client sends `POST /api/logout`
3. Server clears session cookie:
   ```
   Set-Cookie: pb_session=; Max-Age=0
   ```
4. Client redirects to `/login`

---

## Deployment & Operations

### Jetson Deployment

**Systemd Service** (`pokebowl-inventory.service`):
```ini
[Unit]
Description=Poke Bowl Inventory Vision System
After=network.target

[Service]
Type=simple
User=jetson
WorkingDirectory=/home/jetson/Jetson-Orin-Inventory-Vision-System
ExecStart=/usr/bin/python3 backend/main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

**Kiosk Mode** (`chromium-kiosk.service`):
- Launches Chromium in fullscreen
- Opens `http://localhost:8080`
- Auto-starts on boot

**Installation**:
```bash
cd deployment
sudo bash install_service.sh  # Installs systemd service
sudo bash setup_autostart.sh  # Enables auto-start
```

### PC Testing

**Modes**:
- `./start.sh webcam` - Built-in webcam
- `./start.sh phone` - iPhone via USB
- `./start.sh switchable` - Switchable camera UI

**Process Management**:
- PID file: `run/pokebowl.pid`
- Logs: `run/backend.log`
- Manual start: `python3 Testing\ On\ Pc/run_pc_webcam.py`

### Monitoring

**Logs**:
- Application: `/tmp/pokebowl_inventory.log`
- Systemd: `sudo journalctl -u pokebowl-inventory -f`
- Launch: `run/pokebowl_launch.log`

**Health Check**:
```bash
curl http://localhost:8080/health
```

**Status**:
```bash
./status.sh
```

### Configuration

**Environment Variables** (Authentication):
```bash
export AUTH_ENABLED="true"
export AUTH_SESSION_SECRET="<32-char-secret>"
export AUTH_SESSION_TTL="86400"
export AUTH_USERS_JSON='{"username":"$2b$12$..."}'
```

**Environment Variables** (Email Alerts):
```bash
export SMTP_HOST="smtp.gmail.com"
export SMTP_PORT="587"
export SMTP_USER="your-email@gmail.com"
export SMTP_PASS="your-app-password"
export NOTIFY_TO="recipient@example.com"
```

**Configuration File** (`config/config.yaml`):
- Camera settings
- Detector thresholds
- Inventory smoothing
- Alert thresholds
- Server settings

### Troubleshooting

**Camera Not Detected**:
```bash
v4l2-ctl --list-devices  # List cameras
# Update config.yaml: camera.index
```

**Low FPS**:
- Reduce resolution in `config.yaml`
- Lower YOLO input size (`imgsz: 416`)
- Enable maximum performance: `sudo nvpmodel -m 0 && sudo jetson_clocks`

**Database Growth**:
- Automatic cleanup (30-day retention)
- Manual cleanup: `inventory_tracker.cleanup_old_data(days_to_keep=30)`

**Authentication Issues**:
- Check environment variables: `env | grep AUTH_`
- Verify password hash: `python3 generate_password_hash.py <password>`
- Check logs for authentication errors

---

## Summary

This system provides a complete end-to-end inventory tracking solution:

1. **Capture**: USB camera captures frames at 30 FPS
2. **Detect**: YOLO model identifies 40 product classes on GPU
3. **Track**: Temporal smoothing provides stable counts
4. **Persist**: SQLite database stores snapshots, freshness, sales, alerts
5. **Analyze**: Sales attribution and alert engines process data
6. **Notify**: Email alerts for low stock and expiration
7. **Display**: Web dashboard shows real-time data via WebSocket
8. **Secure**: Session-based authentication protects access

The architecture is modular, allowing easy extension and customization. All components are production-ready with error handling, logging, and graceful degradation.





