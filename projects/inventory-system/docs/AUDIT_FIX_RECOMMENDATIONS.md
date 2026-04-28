# Complete Fix Recommendations
## Jetson Orin Inventory Vision System v2.0

This document contains all recommended fixes from the engineering audit, organized by priority with complete code implementations.

---

## 🔴 REQUIRED FIXES (Must Fix Before Production)

### FIX-001: Remove Duplicate Signal Handlers

**File**: `backend/main.py`

**Problem**: Two conflicting signal handler implementations cause race conditions.

**Fix**:
```python
# DELETE lines 252-259 (entire setup_signal_handlers method)
# DELETE any call to setup_signal_handlers() if it exists

# MODIFY lines 384-386 to use proper closure:
async def main():
    """
    Application entry point
    """
    # Create PID file for single-instance protection
    create_pid_file()
    
    try:
        # Determine config path
        config_path = Path(__file__).parent.parent / 'config' / 'config.yaml'
        
        # Create and run system
        system = InventorySystem(config_path)
        
        # Setup signal handlers (FIXED VERSION)
        loop = asyncio.get_event_loop()
        
        # Create handler with proper closure
        def make_shutdown_handler(system_ref):
            def handler():
                asyncio.create_task(system_ref.shutdown())
            return handler
        
        shutdown_handler = make_shutdown_handler(system)
        
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, shutdown_handler)
        
        # Run system
        await system.run()
    
    finally:
        # Always remove PID file
        remove_pid_file()
```

---

### FIX-002: Fix PID File Path Mismatch

**File**: `backend/main.py`

**Problem**: Python uses `/tmp/pokebowl.pid` but shell scripts use `$REPO_ROOT/run/pokebowl.pid`.

**Fix**:
```python
def create_pid_file():
    """
    Create PID file for single-instance protection
    """
    # Use same path as shell scripts
    project_root = Path(__file__).parent.parent
    run_dir = project_root / 'run'
    run_dir.mkdir(exist_ok=True)
    pid_file = run_dir / 'pokebowl.pid'
    
    # Check if already running
    if pid_file.exists():
        try:
            with open(pid_file, 'r') as f:
                old_pid = int(f.read().strip())
            
            # Check if process is still running
            try:
                os.kill(old_pid, 0)
                logger.error(f"Another instance is already running (PID: {old_pid})")
                sys.exit(1)
            except OSError:
                # Process not running, remove stale PID file
                logger.warning(f"Removing stale PID file (PID: {old_pid})")
                pid_file.unlink()
        except Exception as e:
            logger.warning(f"Error checking PID file: {e}")
    
    # Write current PID
    try:
        with open(pid_file, 'w') as f:
            f.write(str(os.getpid()))
        logger.info(f"PID file created: {pid_file}")
    except Exception as e:
        logger.warning(f"Failed to create PID file: {e}")


def remove_pid_file():
    """
    Remove PID file on shutdown
    """
    project_root = Path(__file__).parent.parent
    pid_file = project_root / 'run' / 'pokebowl.pid'
    try:
        if pid_file.exists():
            pid_file.unlink()
            logger.info("PID file removed")
    except Exception as e:
        logger.warning(f"Failed to remove PID file: {e}")
```

---

### FIX-003: Add Missing Database Initialization Call

**File**: `backend/persistence.py`

**Problem**: `_initialize_database()` is never called, so schema is never created.

**Fix**:
```python
def __init__(self, db_path: Optional[Path] = None):
    """
    Initialize persistence manager
    
    Args:
        db_path: Path to SQLite database file (default: data/inventory.db)
    """
    if db_path is None:
        # Default to project_root/data/inventory.db
        project_root = Path(__file__).parent.parent
        data_dir = project_root / 'data'
        data_dir.mkdir(exist_ok=True)
        db_path = data_dir / 'inventory.db'
    
    self.db_path = Path(db_path)
    self.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    self._connection = None
    
    # FIX: Add this line - it was missing!
    self._initialize_database()
    
    self._run_startup_maintenance()
    
    logger.info(f"Persistence manager initialized: {self.db_path}")
```

---

### FIX-004: Clean Up Dead WebSocket Connections

**File**: `backend/server.py`

**Problem**: Dead connections remain in set and slow down broadcasts.

**Fix**:
```python
async def broadcast_frame(self, frame: np.ndarray):
    """
    Broadcast frame to all connected clients
    
    Args:
        frame: Frame to broadcast
    """
    if not self.websockets:
        return
    
    self.latest_frame = frame.copy()
    self.frames_streamed += 1
    
    # Encode once, send to all
    try:
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        frame_b64 = base64.b64encode(buffer).decode('utf-8')
        
        message = {
            'type': 'frame',
            'data': frame_b64,
            'timestamp': time.time()
        }
        
        # Send to all clients concurrently and check for failures
        if self.websockets:
            # Convert to list to avoid modification during iteration
            websocket_list = list(self.websockets)
            results = await asyncio.gather(
                *[ws.send_json(message) for ws in websocket_list],
                return_exceptions=True
            )
            
            # Remove failed connections
            for ws, result in zip(websocket_list, results):
                if isinstance(result, Exception):
                    logger.debug(f"Removing dead WebSocket connection: {result}")
                    self.websockets.discard(ws)
                    try:
                        await ws.close()
                    except:
                        pass
        
    except Exception as e:
        logger.error(f"Failed to broadcast frame: {e}")


# Apply same fix to all broadcast methods:
async def broadcast_inventory(self, inventory: dict):
    """..."""
    if not self.websockets:
        self.latest_inventory = inventory
        return
    
    self.latest_inventory = inventory
    
    message = {
        'type': 'inventory',
        'data': inventory,
        'timestamp': time.time()
    }
    
    if self.websockets:
        websocket_list = list(self.websockets)
        results = await asyncio.gather(
            *[ws.send_json(message) for ws in websocket_list],
            return_exceptions=True
        )
        
        for ws, result in zip(websocket_list, results):
            if isinstance(result, Exception):
                self.websockets.discard(ws)


async def broadcast_stats(self, stats: dict):
    """..."""
    self.latest_stats = stats
    
    if not self.websockets:
        return
    
    message = {
        'type': 'stats',
        'data': stats,
        'timestamp': time.time()
    }
    
    if self.websockets:
        websocket_list = list(self.websockets)
        results = await asyncio.gather(
            *[ws.send_json(message) for ws in websocket_list],
            return_exceptions=True
        )
        
        for ws, result in zip(websocket_list, results):
            if isinstance(result, Exception):
                self.websockets.discard(ws)


async def broadcast_freshness(self, freshness: dict):
    """..."""
    self.latest_freshness = freshness
    
    if not self.websockets:
        return
    
    message = {
        'type': 'freshness',
        'data': freshness,
        'timestamp': time.time()
    }
    
    if self.websockets:
        websocket_list = list(self.websockets)
        results = await asyncio.gather(
            *[ws.send_json(message) for ws in websocket_list],
            return_exceptions=True
        )
        
        for ws, result in zip(websocket_list, results):
            if isinstance(result, Exception):
                self.websockets.discard(ws)


async def broadcast_sales(self, sales: list):
    """..."""
    self.latest_sales = sales
    
    if not self.websockets:
        return
    
    message = {
        'type': 'sales',
        'data': sales,
        'timestamp': time.time()
    }
    
    if self.websockets:
        websocket_list = list(self.websockets)
        results = await asyncio.gather(
            *[ws.send_json(message) for ws in websocket_list],
            return_exceptions=True
        )
        
        for ws, result in zip(websocket_list, results):
            if isinstance(result, Exception):
                self.websockets.discard(ws)


async def broadcast_alerts(self, alerts: list):
    """..."""
    self.latest_alerts = alerts
    
    if not self.websockets:
        return
    
    message = {
        'type': 'alerts',
        'data': alerts,
        'timestamp': time.time()
    }
    
    if self.websockets:
        websocket_list = list(self.websockets)
        results = await asyncio.gather(
            *[ws.send_json(message) for ws in websocket_list],
            return_exceptions=True
        )
        
        for ws, result in zip(websocket_list, results):
            if isinstance(result, Exception):
                self.websockets.discard(ws)
```

---

### FIX-005: Fix Frontend WebSocket Reconnection Timer Leak

**File**: `frontend/index.html`

**Problem**: Multiple reconnection timers can stack up under flaky network conditions.

**Fix**:
```javascript
// Find the connect() function (around line 734)
function connect() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    
    console.log('Connecting to:', wsUrl);
    
    // Close existing connection if any
    if (ws && ws.readyState !== WebSocket.CLOSED) {
        ws.close();
    }
    
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        console.log('WebSocket connected');
        isConnected = true;
        updateConnectionStatus(true);
        
        // Always clear existing interval first
        if (reconnectInterval) {
            clearInterval(reconnectInterval);
            reconnectInterval = null;
        }
    };

    ws.onmessage = (event) => {
        try {
            const message = JSON.parse(event.data);
            handleMessage(message);
        } catch (e) {
            console.error('Error parsing message:', e);
        }
    };

    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
    };

    ws.onclose = () => {
        console.log('WebSocket disconnected');
        isConnected = false;
        updateConnectionStatus(false);
        
        // Always clear existing interval first
        if (reconnectInterval) {
            clearInterval(reconnectInterval);
        }
        
        // Only reconnect if connection was not intentionally closed
        if (ws.readyState === WebSocket.CLOSED) {
            reconnectInterval = setInterval(() => {
                // Check if we should still reconnect
                if (!ws || ws.readyState === WebSocket.CLOSED) {
                    console.log('Attempting to reconnect...');
                    connect();
                } else {
                    // Connection restored, clear interval
                    clearInterval(reconnectInterval);
                    reconnectInterval = null;
                }
            }, 3000);
        }
    };
}
```

---

## 🟡 RECOMMENDED FIXES (Should Fix for Stability)

### FIX-006: Implement Persistent Database Connection

**File**: `backend/persistence.py`

**Problem**: New connection created for every operation, preventing connection pooling.

**Fix**:
```python
def __init__(self, db_path: Optional[Path] = None):
    """..."""
    # ... existing path setup ...
    
    self.db_path = Path(db_path)
    self.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create persistent connection
    self._connection = None
    self._connection_lock = threading.Lock()
    
    self._initialize_database()
    self._run_startup_maintenance()
    
    # Open persistent connection
    self._ensure_connection()
    
    logger.info(f"Persistence manager initialized: {self.db_path}")


def _ensure_connection(self):
    """Ensure database connection is open"""
    if self._connection is None:
        self._connection = sqlite3.connect(str(self.db_path), timeout=10.0)
        self._connection.row_factory = sqlite3.Row
        
        # Enable WAL mode (persistent)
        self._connection.execute('PRAGMA journal_mode=WAL')
        self._connection.execute('PRAGMA synchronous=NORMAL')
        
        # Set busy timeout for better concurrency
        self._connection.execute('PRAGMA busy_timeout=5000')


@contextmanager
def _get_connection(self):
    """
    Context manager for database connections
    Uses persistent connection with thread safety
    """
    self._ensure_connection()
    
    try:
        yield self._connection
        self._connection.commit()
    except Exception as e:
        self._connection.rollback()
        logger.error(f"Database transaction failed: {e}")
        raise


def close(self):
    """
    Close database connection and cleanup
    """
    if self._connection:
        try:
            self._connection.close()
            self._connection = None
            logger.info("Database connection closed")
        except Exception as e:
            logger.error(f"Error closing database connection: {e}")
```

---

### FIX-007: Fix Startup Maintenance Query

**File**: `backend/persistence.py`

**Problem**: Preserves records by ID instead of timestamp, inefficient query.

**Fix**:
```python
def _run_startup_maintenance(self, retention_days: int = 30):
    """
    Run maintenance tasks on startup
    Cleans up old data to prevent unbounded growth
    
    Args:
        retention_days: Number of days of data to retain (default: 30)
    """
    try:
        cutoff_time = datetime.now(timezone.utc).timestamp() - (retention_days * 86400)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Count records before cleanup
            cursor.execute("SELECT COUNT(*) as count FROM inventory_snapshots")
            snapshots_before = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM alerts_log")
            alerts_before = cursor.fetchone()['count']
            
            # Delete old inventory snapshots (keep recent 100 by timestamp)
            cursor.execute("""
                DELETE FROM inventory_snapshots 
                WHERE timestamp_utc < ? 
                AND id NOT IN (
                    SELECT id FROM inventory_snapshots 
                    ORDER BY timestamp_utc DESC 
                    LIMIT 100
                )
            """, (cutoff_time,))
            snapshots_deleted = cursor.rowcount
            
            # Delete old alerts (keep recent 100 by timestamp)
            cursor.execute("""
                DELETE FROM alerts_log 
                WHERE timestamp_utc < ?
                AND id NOT IN (
                    SELECT id FROM alerts_log 
                    ORDER BY timestamp_utc DESC 
                    LIMIT 100
                )
            """, (cutoff_time,))
            alerts_deleted = cursor.rowcount
            
            if snapshots_deleted > 0 or alerts_deleted > 0:
                logger.info(f"Startup maintenance: deleted {snapshots_deleted} old snapshots, "
                          f"{alerts_deleted} old alerts (retention: {retention_days} days)")
                
    except Exception as e:
        logger.warning(f"Startup maintenance failed (non-critical): {e}")
```

---

### FIX-008: Make Camera Reconnection Async

**File**: `backend/camera.py`

**Problem**: Synchronous `time.sleep()` blocks event loop during reconnection.

**Fix**:
```python
async def reconnect_async(self, max_attempts: int = 5, retry_delay: float = 2.0) -> bool:
    """
    Attempt to reconnect to camera (async version)
    
    Args:
        max_attempts: Maximum number of reconnection attempts
        retry_delay: Delay between attempts in seconds
        
    Returns:
        True if reconnection successful
    """
    import asyncio
    
    logger.warning("Attempting camera reconnection...")
    self.release()
    
    for attempt in range(1, max_attempts + 1):
        logger.info(f"Reconnection attempt {attempt}/{max_attempts}")
        await asyncio.sleep(retry_delay)  # Non-blocking
        
        if self.open():
            logger.info("Camera reconnected successfully")
            return True
    
    logger.error("Camera reconnection failed")
    return False


# Keep synchronous version for backward compatibility
def reconnect(self, max_attempts: int = 5, retry_delay: float = 2.0) -> bool:
    """
    Attempt to reconnect to camera (synchronous version)
    Use reconnect_async() in async contexts
    """
    logger.warning("Attempting camera reconnection...")
    self.release()
    
    for attempt in range(1, max_attempts + 1):
        logger.info(f"Reconnection attempt {attempt}/{max_attempts}")
        time.sleep(retry_delay)
        
        if self.open():
            logger.info("Camera reconnected successfully")
            return True
    
    logger.error("Camera reconnection failed")
    return False
```

**Then update `backend/server.py`**:
```python
# In stream_loop() method, around line 688:
if not success or frame is None:
    logger.warning("Failed to capture frame, attempting reconnection...")
    if not await self.camera.reconnect_async():  # Use async version
        await asyncio.sleep(1.0)
        continue
    success, frame = self.camera.read()
    if not success:
        await asyncio.sleep(1.0)
        continue
```

---

### FIX-009: Normalize Product Names for Freshness Tracking

**File**: `backend/inventory_persistent.py`

**Problem**: Case-sensitive product names create duplicate freshness records.

**Fix**:
```python
def _update_freshness_tracking(self, inventory: Dict[str, int], current_time: float):
    """
    Update freshness tracking for products in current inventory
    
    Args:
        inventory: Current inventory dictionary
        current_time: Current timestamp
    """
    if not self.persistence:
        return
    
    try:
        for product_name, count in inventory.items():
            # Normalize product name to lowercase for consistency
            product_key = product_name.lower()
            
            # Check if this product should be tracked for freshness
            if self.FRESHNESS_TRACKED_PRODUCTS is None:
                # Track all products
                is_tracked = True
            else:
                # Track only specific products
                is_tracked = any(tracked.lower() in product_key 
                               for tracked in self.FRESHNESS_TRACKED_PRODUCTS)
            
            if is_tracked and count > 0:
                # Check if we already have freshness data (using normalized key)
                if product_key not in self.freshness_state:
                    # First time seeing this product - initialize freshness
                    self.persistence.update_product_freshness(
                        product_name,  # Store original case in DB
                        first_seen_utc=current_time,
                        expiration_days=self.expiration_days
                    )
                    
                    # Update in-memory cache with normalized key
                    freshness_data = self.persistence.get_product_freshness(product_name)
                    if freshness_data:
                        self.freshness_state[product_key] = freshness_data
                        logger.info(f"Started freshness tracking: {product_name}")
                else:
                    # Update existing freshness record (updates last_seen)
                    first_seen = self.freshness_state[product_key]['first_seen_utc']
                    self.persistence.update_product_freshness(
                        product_name,  # Use original case from inventory
                        first_seen_utc=first_seen,
                        expiration_days=self.expiration_days
                    )
                    
                    # Refresh in-memory cache
                    freshness_data = self.persistence.get_product_freshness(product_name)
                    if freshness_data:
                        self.freshness_state[product_key] = freshness_data
        
    except Exception as e:
        logger.error(f"Failed to update freshness tracking: {e}")
```

---

### FIX-010: Make PC Testing Auth Configurable

**File**: `Testing On Pc/run_pc_webcam.py`

**Problem**: Authentication hardcoded to False, security risk.

**Fix**:
```python
# Around line 272-279, replace:
# Initialize web server (original code) - AUTH DISABLED for PC webcam
frontend_dir = PARENT_DIR / 'frontend'

# Check if auth should be enabled (respect environment variable)
import os
auth_enabled_env = os.getenv('AUTH_ENABLED', 'false').lower()
enable_auth = auth_enabled_env == 'true'

if not enable_auth:
    logger.info("Authentication disabled for PC testing (set AUTH_ENABLED=true to enable)")

server = VideoStreamServer(
    host=config['server']['host'],
    port=config['server']['port'],
    frontend_dir=frontend_dir,
    enable_auth=enable_auth  # Configurable, not hardcoded
)
```

---

### FIX-011: Add Graceful Degradation for Camera Failures

**File**: `backend/server.py`

**Problem**: Infinite retry loop if camera permanently fails.

**Fix**:
```python
async def stream_loop(self):
    """
    Main streaming loop
    Captures frames, runs inference, updates inventory, and broadcasts
    """
    logger.info("Starting stream loop...")
    self.is_running = True
    
    frame_count = 0
    last_stats_time = time.time()
    stats_interval = 1.0  # Update stats every second
    
    # Track consecutive camera failures
    consecutive_camera_failures = 0
    max_consecutive_failures = 20  # 20 failures = ~20 seconds
    
    while self.is_running:
        loop_start = time.time()
        
        # Capture frame
        success, frame = self.camera.read()
        
        if not success or frame is None:
            consecutive_camera_failures += 1
            logger.warning(f"Failed to capture frame (failure {consecutive_camera_failures}/{max_consecutive_failures})")
            
            # If too many failures, trigger alert and pause
            if consecutive_camera_failures >= max_consecutive_failures:
                logger.error("Camera has failed too many times. Entering degraded mode.")
                # Send alert if alert engine available
                if hasattr(self.inventory_tracker, 'alert_engine') and self.inventory_tracker.alert_engine:
                    # Create system alert
                    from alerts import Alert, AlertType, AlertSeverity
                    alert = Alert(
                        alert_type=AlertType.LOW_STOCK,  # Reuse type, or create SYSTEM type
                        product_name="System",
                        severity=AlertSeverity.CRITICAL,
                        message="Camera has failed repeatedly. System in degraded mode.",
                        timestamp_utc=time.time(),
                        metadata={'consecutive_failures': consecutive_camera_failures}
                    )
                    # Process alert
                    self.inventory_tracker.alert_engine._process_alert(alert, time.time())
                
                # Wait longer before retry
                await asyncio.sleep(10.0)
                consecutive_camera_failures = 0  # Reset counter
                continue
            
            # Attempt reconnection
            if not await self.camera.reconnect_async():
                await asyncio.sleep(1.0)
                continue
            
            # Reset failure counter on successful reconnect
            consecutive_camera_failures = 0
            success, frame = self.camera.read()
            if not success:
                await asyncio.sleep(1.0)
                continue
        
        # Reset failure counter on successful read
        consecutive_camera_failures = 0
        
        # ... rest of loop continues normally ...
```

---

### FIX-012: Add Rate Limiting to Login Endpoint

**File**: `backend/server.py`

**Problem**: No protection against brute force attacks.

**Fix**:
```python
# Add at top of VideoStreamServer class:
from collections import defaultdict
from datetime import datetime, timedelta

class VideoStreamServer:
    def __init__(self, ...):
        # ... existing init ...
        
        # Rate limiting for login
        self.login_attempts = defaultdict(list)  # {ip: [timestamps]}
        self.max_login_attempts = 5
        self.login_window_seconds = 60
    
    async def handle_login(self, request: web.Request) -> web.Response:
        """Handle login POST request"""
        if not self.auth_enabled:
            return web.json_response({'success': True, 'message': 'Authentication disabled'})
        
        if not self.auth_manager:
            return web.json_response({'success': False, 'message': 'Authentication not configured'}, status=503)
        
        # Rate limiting check
        client_ip = request.remote
        now = datetime.now()
        
        # Clean old attempts
        if client_ip in self.login_attempts:
            self.login_attempts[client_ip] = [
                ts for ts in self.login_attempts[client_ip]
                if (now - ts).total_seconds() < self.login_window_seconds
            ]
        
        # Check if rate limited
        if len(self.login_attempts.get(client_ip, [])) >= self.max_login_attempts:
            logger.warning(f"Rate limit exceeded for {client_ip}")
            return web.json_response({
                'success': False,
                'message': 'Too many login attempts. Please try again later.'
            }, status=429)
        
        try:
            data = await request.json()
            username = data.get('username', '').strip()
            password = data.get('password', '')
            
            if not username or not password:
                return web.json_response({'success': False, 'message': 'Username and password required'}, status=400)
            
            # Authenticate user
            session_token = self.auth_manager.authenticate(username, password)
            
            if session_token:
                # Record successful login (clear failed attempts)
                self.login_attempts[client_ip] = []
                
                # Create response with session cookie
                response = web.json_response({'success': True, 'message': 'Login successful'})
                
                # ... rest of cookie setup ...
                return response
            else:
                # Record failed attempt
                self.login_attempts[client_ip].append(now)
                
                return web.json_response({'success': False, 'message': 'Invalid username or password'}, status=401)
        
        except Exception as e:
            logger.error(f"Login error: {e}")
            return web.json_response({'success': False, 'message': 'Login failed'}, status=500)
```

---

### FIX-013: Improve Sales Attribution Validation Clarity

**File**: `backend/sales_attribution.py`

**Problem**: Variable naming is confusing, logic is correct but hard to understand.

**Fix**:
```python
def _validate_decrease(self, product_name: str, current_timestamp: float) -> bool:
    """
    Validate that a decrease has persisted for required number of intervals
    
    This method checks that the product count has remained at or below
    the decreased level across multiple consecutive snapshots, indicating
    a real sale rather than temporary detection noise.
    
    Args:
        product_name: Product to validate
        current_timestamp: Current timestamp
        
    Returns:
        True if decrease is validated, False otherwise
    """
    # Check if we have enough snapshot history
    if len(self.snapshot_history) < self.confirm_intervals + 1:
        return False
    
    # Get recent snapshots
    recent_snapshots = list(self.snapshot_history)[-(self.confirm_intervals + 1):]
    
    # Extract counts for this product across snapshots
    counts = [inv.get(product_name, 0) for _, inv in recent_snapshots]
    
    # baseline_count: count at first snapshot (before decrease)
    # subsequent_counts: counts in following snapshots (after decrease)
    baseline_count = counts[0]
    subsequent_counts = counts[1:]
    
    # Check if count has been consistently decreasing or stable at lower level
    # A valid decrease means:
    # 1. All subsequent counts are <= baseline (decrease persisted)
    # 2. At least one subsequent count is < baseline (actual decrease occurred)
    for count in subsequent_counts:
        if count > baseline_count:
            # Count increased back - not a persistent decrease
            return False
        if count == baseline_count:
            # Count returned to baseline - decrease was temporary
            return False
    
    # Count has remained below baseline across all intervals
    # This indicates a persistent, validated decrease
    return True
```

---

## 🟢 OPTIONAL FIXES (Nice to Have)

### FIX-014: Add Reset Method to PersistentInventoryTracker

**File**: `backend/inventory_persistent.py`

**Fix**:
```python
def reset(self):
    """
    Reset all tracking history and counters
    """
    # Reset base class
    super().reset()
    
    # Reset persistence-specific state
    self.last_snapshot_time = 0
    self.last_inventory_snapshot.clear()
    self.freshness_state.clear()
    
    # Reset sales attribution
    if self.sales_attribution:
        self.sales_attribution.reset()
    
    # Alert engine doesn't have reset, but could clear active alerts
    if self.alert_engine:
        self.alert_engine.active_alerts.clear()
    
    logger.info("Persistent inventory tracker reset")
```

---

### FIX-015: Enhance Health Check Endpoint

**File**: `backend/server.py`

**Fix**:
```python
async def handle_health(self, request: web.Request) -> web.Response:
    """Health check endpoint with component status"""
    uptime = time.time() - self.start_time
    
    # Check component health
    camera_ok = False
    detector_ok = False
    streaming_ok = False
    
    if self.stream_manager:
        if self.stream_manager.camera:
            camera_ok = self.stream_manager.camera.is_healthy()
        if self.stream_manager.detector:
            detector_ok = self.stream_manager.detector.is_loaded
        streaming_ok = self.stream_manager.is_running
    
    # Overall status
    if camera_ok and detector_ok and streaming_ok:
        status = 'healthy'
    elif camera_ok or detector_ok or streaming_ok:
        status = 'degraded'
    else:
        status = 'unhealthy'
    
    health_data = {
        'status': status,
        'uptime_seconds': uptime,
        'active_connections': len(self.websockets),
        'frames_streamed': self.frames_streamed,
        'components': {
            'camera': camera_ok,
            'detector': detector_ok,
            'streaming': streaming_ok
        }
    }
    
    # Return appropriate status code
    status_code = 200 if status == 'healthy' else (503 if status == 'unhealthy' else 200)
    
    return web.json_response(health_data, status=status_code)
```

---

### FIX-016: Add Database Backup Mechanism

**File**: `backend/persistence.py`

**Fix**:
```python
def backup_database(self, backup_path: Optional[Path] = None) -> bool:
    """
    Create a backup of the database
    
    Args:
        backup_path: Path for backup file (default: data/inventory.db.backup)
        
    Returns:
        True if backup successful, False otherwise
    """
    try:
        if backup_path is None:
            backup_path = self.db_path.parent / f"{self.db_path.stem}.backup"
        
        backup_path = Path(backup_path)
        
        # Use SQLite backup API for safe backup
        if self._connection:
            # Backup from current connection
            backup_conn = sqlite3.connect(str(backup_path))
            self._connection.backup(backup_conn)
            backup_conn.close()
        else:
            # Create new connection for backup
            source_conn = sqlite3.connect(str(self.db_path))
            backup_conn = sqlite3.connect(str(backup_path))
            source_conn.backup(backup_conn)
            source_conn.close()
            backup_conn.close()
        
        logger.info(f"Database backed up to {backup_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to backup database: {e}")
        return False


# Add to PersistentInventoryTracker:
def backup_database(self) -> bool:
    """Backup database"""
    if self.persistence:
        return self.persistence.backup_database()
    return False
```

---

### FIX-017: Add Sanity Check for Detection Counts

**File**: `backend/inventory.py`

**Fix**:
```python
# Add constant at top of file
MAX_DETECTIONS_PER_FRAME = 100  # Sanity limit

def update(self, detections: List[dict]):
    """
    Update inventory with new detections from a frame
    
    Args:
        detections: List of detection dicts with 'class_id' key
    """
    # Sanity check: reject frames with excessive detections
    if len(detections) > MAX_DETECTIONS_PER_FRAME:
        logger.warning(f"Rejecting frame with {len(detections)} detections (max: {MAX_DETECTIONS_PER_FRAME})")
        return
    
    self.frame_count += 1
    self.total_detections += len(detections)
    
    # ... rest of method unchanged ...
```

---

### FIX-018: Fix Alert Cooldown Comparison

**File**: `backend/alerts.py`

**Fix**:
```python
def _check_cooldown(self, alert_type: str, product_name: str, current_time: float) -> bool:
    """
    Check if alert cooldown has passed
    
    Args:
        alert_type: Type of alert
        product_name: Product name
        current_time: Current timestamp
        
    Returns:
        True if cooldown passed, False otherwise
    """
    key = (alert_type, product_name)
    
    if key not in self.last_alert_time:
        return True
    
    time_since_last = current_time - self.last_alert_time[key]
    
    # Use <= to match intended behavior (suppress if within cooldown period)
    if time_since_last <= self.alert_cooldown_seconds:
        self.alerts_suppressed_by_cooldown += 1
        logger.debug(f"⊗ Alert suppressed by cooldown: {alert_type} - {product_name} "
                    f"({time_since_last:.0f}s <= {self.alert_cooldown_seconds:.0f}s)")
        return False
    
    return True
```

---

### FIX-019: Add Pagination to Sales Log API

**File**: `backend/server.py`

**Fix**:
```python
async def handle_sales(self, request: web.Request) -> web.Response:
    """Return sales log with pagination"""
    # Check authentication
    if not await self.check_auth(request):
        return web.json_response({'error': 'Unauthorized'}, status=401)
    
    # Get pagination parameters
    limit = int(request.query.get('limit', 100))
    offset = int(request.query.get('offset', 0))
    
    # Limit max page size
    limit = min(limit, 500)
    
    # Get sales from tracker if available
    if hasattr(self.inventory_tracker, 'get_sales_history'):
        sales = self.inventory_tracker.get_sales_history(limit=limit + offset)
        # Apply offset
        sales = sales[offset:offset + limit]
    else:
        sales = self.latest_sales[offset:offset + limit]
    
    return web.json_response({
        'sales': sales,
        'limit': limit,
        'offset': offset,
        'total': len(self.latest_sales) if hasattr(self, 'latest_sales') else len(sales)
    })
```

---

### FIX-020: Make Log File Path Configurable

**File**: `backend/main.py`

**Fix**:
```python
# At top of file, after imports:
LOG_FILE_PATH = os.getenv('POKEBOWL_LOG_FILE', '/tmp/pokebowl_inventory.log')

# In logging configuration (around line 25):
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE_PATH)
    ]
)
```

---

### FIX-021: Add CORS Headers for Cross-Origin Support

**File**: `backend/server.py`

**Fix**:
```python
# In setup_routes() method, add middleware:
from aiohttp_cors import setup as cors_setup, ResourceOptions

def setup_routes(self):
    """Setup HTTP and WebSocket routes"""
    # ... existing routes ...
    
    # Setup CORS
    cors = cors_setup(self.app, defaults={
        "*": ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
            allow_methods="*"
        )
    })
    
    # Add CORS to all routes
    for route in list(self.app.router.routes()):
        cors.add(route)
```

**Note**: Requires `aiohttp-cors` package: `pip install aiohttp-cors`

---

## 📋 IMPLEMENTATION CHECKLIST

### Phase 1: Critical Fixes (REQUIRED)
- [ ] FIX-001: Remove duplicate signal handlers
- [ ] FIX-002: Fix PID file path mismatch
- [ ] FIX-003: Add database initialization call
- [ ] FIX-004: Clean up dead WebSocket connections
- [ ] FIX-005: Fix frontend reconnection timer leak

### Phase 2: Stability Fixes (RECOMMENDED)
- [ ] FIX-006: Implement persistent database connection
- [ ] FIX-007: Fix startup maintenance query
- [ ] FIX-008: Make camera reconnection async
- [ ] FIX-009: Normalize product names
- [ ] FIX-010: Make PC testing auth configurable
- [ ] FIX-011: Add graceful degradation for camera
- [ ] FIX-012: Add rate limiting to login
- [ ] FIX-013: Improve sales attribution clarity

### Phase 3: Enhancements (OPTIONAL)
- [ ] FIX-014: Add reset method
- [ ] FIX-015: Enhance health check
- [ ] FIX-016: Add database backup
- [ ] FIX-017: Add detection sanity check
- [ ] FIX-018: Fix alert cooldown comparison
- [ ] FIX-019: Add pagination to sales API
- [ ] FIX-020: Make log file configurable
- [ ] FIX-021: Add CORS headers

---

## 🧪 TESTING RECOMMENDATIONS

After implementing fixes, test:

1. **Signal Handling**: Start system, press Ctrl+C 10 times rapidly → should shutdown cleanly
2. **PID File**: Start, check `run/pokebowl.pid` exists, stop → file removed
3. **Database**: Delete `data/inventory.db*`, start → schema created automatically
4. **WebSocket**: Connect 10 browsers, disconnect 5 → dead connections cleaned up
5. **Camera**: Unplug camera, wait 30s → graceful degradation, reconnect → resumes
6. **Rate Limiting**: Attempt login 10 times rapidly → blocked after 5 attempts
7. **Freshness**: Detect "Mango" and "mango" → single freshness record

---

**END OF RECOMMENDATIONS**

