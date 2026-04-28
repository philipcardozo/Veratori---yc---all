"""
Veratori Camera Demo Server
Streams YOLO-annotated frames from the See3CAM_24CUG via MJPEG over HTTP.

Endpoints:
  GET /stream        — MJPEG stream (use as <img src="...">)
  POST /reconnect    — Re-initialise the camera
  GET /status        — JSON health check

Run (from inventory-system folder):
  "/Users/felipecardozo/Desktop/Company Veratori /Veratori/.venv/bin/python" camera_server.py
"""

import cv2
import threading
import time
import json
import os
import subprocess
import webbrowser
from http.server import BaseHTTPRequestHandler
from socketserver import ThreadingMixIn, TCPServer
from ultralytics import YOLO

class ThreadingHTTPServer(ThreadingMixIn, TCPServer):
    allow_reuse_address = True
    daemon_threads = True

# ── Config ────────────────────────────────────────────────────────────────────
PORT       = 5001
MODEL_PATH = os.path.join(os.path.dirname(__file__), "models/yolov8n.pt")
CONF_THRESH = 0.40
FRAME_W     = 640
FRAME_H     = 480

# Colour palette for bounding boxes (one per class, cycling)
PALETTE = [
    (16,185,129), (59,130,246), (245,158,11), (239,68,68),
    (139,92,246), (236,72,153), (14,165,233), (34,197,94),
    (251,146,60), (99,102,241),
]

# ── Shared state ──────────────────────────────────────────────────────────────
lock             = threading.Lock()
latest_frame     = None   # bytes (JPEG)
yolo_enabled     = False  # toggled by POST /yolo/toggle
camera_status    = {"connected": False, "error": None, "fps": 0, "yolo": False}
model            = None
latest_detections = []    # list of {label, conf, count} updated each frame
_last_empty_log  = 0.0    # throttle for "no detections" spam (1/sec)

# ── Camera + inference thread ─────────────────────────────────────────────────
# Keywords that identify phone / virtual cameras — always tried last
_PHONE_KEYWORDS   = ["iphone", "ipad", "android", "continuity", "droidcam",
                     "epoccam", "camo", "ndccam", "obs virtual", "mmhmm"]
# Keywords that identify built-in cameras — tried before phones but after USB
_BUILTIN_KEYWORDS = ["facetime", "built-in", "builtin", "integrated", "isight"]

def _ranked_camera_indices():
    """
    Query system_profiler for all AVFoundation cameras and return their indices
    sorted into three priority tiers:
      Tier 0 — external USB/IP cameras  (e.g. See3CAM, webcam)
      Tier 1 — built-in cameras         (e.g. FaceTime HD)
      Tier 2 — phone / virtual cameras  (e.g. iPhone Continuity Camera)
    Returns a flat list of (index, name, tier) tuples in priority order.
    """
    try:
        result = subprocess.run(
            ["system_profiler", "SPCameraDataType", "-json"],
            capture_output=True, text=True, timeout=5
        )
        cameras = json.loads(result.stdout).get("SPCameraDataType", [])
        if cameras:
            tiers = {0: [], 1: [], 2: []}
            for i, cam in enumerate(cameras):
                name = cam.get("_name", f"Camera {i}")
                nl   = name.lower()
                if any(k in nl for k in _PHONE_KEYWORDS):
                    tier = 2
                elif any(k in nl for k in _BUILTIN_KEYWORDS):
                    tier = 1
                else:
                    tier = 0   # external / USB — highest priority
                tiers[tier].append((i, name))
                print(f"[camera] [{['USB/ext','built-in','phone'][tier]}] index {i} → {name}")
            ranked = []
            for t in (0, 1, 2):
                ranked.extend([(i, n, t) for i, n in tiers[t]])
            return ranked
    except Exception as e:
        print(f"[camera] system_profiler lookup failed: {e}")
    # Fallback: just try indices 0-6 with no tier info
    return [(i, f"index {i}", 1) for i in range(7)]

def _try_open(idx, name):
    """Try to open camera at idx; return cap if live frames confirmed, else None."""
    cap = cv2.VideoCapture(idx, cv2.CAP_AVFOUNDATION)
    if not cap.isOpened():
        cap.release()
        return None
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  FRAME_W)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_H)
    for _ in range(5):
        ret, frame = cap.read()
        if ret and frame is not None:
            print(f"[camera] ✓ Live frames from '{name}' (index {idx})")
            return cap
        time.sleep(0.1)
    print(f"[camera] ✗ '{name}' (index {idx}) opened but no frames — skipping")
    cap.release()
    return None

def find_best_camera():
    """
    Open the best available camera using a three-tier priority:
      1st — external USB cameras  (See3CAM, webcams, …)
      2nd — built-in camera       (FaceTime HD, …)
      3rd — phone / virtual cam   (iPhone Continuity, DroidCam, …)
    Stops and returns the first tier that yields a working camera.
    """
    ranked = _ranked_camera_indices()

    # Group by tier so we don't fall through to phone if a USB cam exists
    tiers: dict[int, list] = {0: [], 1: [], 2: []}
    for idx, name, tier in ranked:
        tiers[tier].append((idx, name))

    for tier_num in (0, 1, 2):
        entries = tiers[tier_num]
        if not entries:
            continue
        tier_label = ['USB/external', 'built-in', 'phone/virtual'][tier_num]
        print(f"[camera] Trying tier {tier_num} ({tier_label}): {[n for _,n in entries]}")
        for idx, name in entries:
            cap = _try_open(idx, name)
            if cap:
                return cap
        # If at least one camera existed in this tier but none worked, still
        # continue to the next tier (e.g. See3CAM unplugged → fall to built-in).

    return None

# Keep old name as alias so any external callers still work
find_see3cam = find_best_camera

def draw_detections(frame, results):
    for r in results:
        for box in r.boxes:
            x1,y1,x2,y2 = map(int, box.xyxy[0])
            cls   = int(box.cls[0])
            conf  = float(box.conf[0])
            label = model.names[cls] if hasattr(model, 'names') else str(cls)
            color = PALETTE[cls % len(PALETTE)]
            # Box
            cv2.rectangle(frame, (x1,y1), (x2,y2), color, 2)
            # Label background
            text  = f"{label}  {conf:.0%}"
            (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            cv2.rectangle(frame, (x1, y1-th-6), (x1+tw+6, y1), color, -1)
            cv2.putText(frame, text, (x1+3, y1-3),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255,255,255), 1, cv2.LINE_AA)
    return frame

def capture_loop():
    global latest_frame, camera_status, model, _last_empty_log, latest_detections

    print("[server] Loading YOLO model…")
    try:
        model = YOLO(MODEL_PATH)
        print(f"[server] Model loaded: {MODEL_PATH}")
    except Exception as e:
        print(f"[server] Model load failed: {e}")
        camera_status["error"] = f"Model load failed: {e}"
        return

    cap = find_best_camera()
    if cap is None:
        camera_status["error"] = "No camera found (USB, built-in, or phone)"
        print("[camera] ERROR:", camera_status["error"])
        _serve_error_frame()
        return

    camera_status["connected"] = True
    camera_status["error"]     = None

    t0 = time.time()
    fc = 0

    while True:
        ok, frame = cap.read()
        if not ok:
            camera_status["connected"] = False
            camera_status["error"] = "Frame read failed — camera disconnected?"
            print("[camera] Frame read failed, waiting 2s…")
            time.sleep(2)
            cap.release()
            cap = find_best_camera()
            if cap is None:
                _serve_error_frame()
                continue
            camera_status["connected"] = True
            camera_status["error"] = None
            continue

        # Run YOLO only when enabled
        if yolo_enabled:
            try:
                results = model(frame, conf=CONF_THRESH, verbose=False)
                frame   = draw_detections(frame, results)

                # Aggregate detections by label
                counts = {}
                for r in results:
                    for box in r.boxes:
                        cls   = int(box.cls[0])
                        conf  = float(box.conf[0])
                        label = model.names[cls] if hasattr(model, 'names') else str(cls)
                        if label not in counts:
                            counts[label] = {"label": label, "count": 0, "conf": 0.0}
                        counts[label]["count"] += 1
                        counts[label]["conf"] = max(counts[label]["conf"], conf)

                new_detections = sorted(counts.values(), key=lambda x: -x["count"])
                with lock:
                    latest_detections = new_detections

                if new_detections:
                    print(f"[yolo] DETECTED: { {d['label']: d['count'] for d in new_detections} }")
                else:
                    now = time.time()
                    if now - _last_empty_log >= 1.0:
                        print(f"[yolo] no detections (conf={CONF_THRESH})")
                        _last_empty_log = now
            except Exception as e:
                print(f"[yolo] Inference error: {e}")
        else:
            with lock:
                latest_detections = []

        # FPS overlay
        fc += 1
        elapsed = time.time() - t0
        if elapsed >= 1.0:
            camera_status["fps"]  = round(fc / elapsed, 1)
            camera_status["yolo"] = yolo_enabled
            fc = 0
            t0 = time.time()

        _, jpg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 82])
        with lock:
            latest_frame = jpg.tobytes()

    cap.release()

_reconnecting = False
def reconnect():
    """Restart the capture thread (debounced — ignores if already reconnecting)."""
    global latest_frame, camera_status, _reconnecting
    if _reconnecting:
        return
    _reconnecting = True
    camera_status = {"connected": False, "error": "Reconnecting…", "fps": 0}
    with lock:
        latest_frame = None
    def _start():
        global _reconnecting
        capture_loop()
        _reconnecting = False
    t = threading.Thread(target=_start, daemon=True)
    t.start()

def _serve_error_frame():
    """Push a black frame with an error message when camera is unavailable."""
    global latest_frame
    blank = __import__('numpy').zeros((FRAME_H, FRAME_W, 3), dtype='uint8')
    msg   = camera_status.get("error", "No camera")
    cv2.putText(blank, msg, (10, FRAME_H//2),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (239,68,68), 1, cv2.LINE_AA)
    cv2.putText(blank, "Click Reconnect to retry", (10, FRAME_H//2+28),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (148,163,184), 1, cv2.LINE_AA)
    _, jpg = cv2.imencode('.jpg', blank)
    with lock:
        latest_frame = jpg.tobytes()

# ── HTTP handler ───────────────────────────────────────────────────────────────
class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # suppress per-request logs

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_GET(self):
        if self.path == "/stream":
            self.send_response(200)
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
            self._cors()
            self.end_headers()
            try:
                while True:
                    with lock:
                        frame = latest_frame
                    if frame:
                        self.wfile.write(b"--frame\r\n")
                        self.wfile.write(b"Content-Type: image/jpeg\r\n\r\n")
                        self.wfile.write(frame)
                        self.wfile.write(b"\r\n")
                        self.wfile.flush()
                    time.sleep(0.033)   # ~30 fps cap
            except (BrokenPipeError, ConnectionResetError):
                pass

        elif self.path.startswith("/snapshot"):
            with lock:
                frame = latest_frame
            if frame:
                self.send_response(200)
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Content-Length", len(frame))
                self.send_header("Cache-Control", "no-cache, no-store")
                self._cors()
                self.end_headers()
                self.wfile.write(frame)
            else:
                self.send_response(503)
                self._cors()
                self.end_headers()

        elif self.path == "/status":
            body = json.dumps(camera_status).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", len(body))
            self._cors()
            self.end_headers()
            self.wfile.write(body)

        elif self.path == "/detections":
            with lock:
                payload = list(latest_detections)
            body = json.dumps(payload).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", len(body))
            self.send_header("Cache-Control", "no-cache, no-store")
            self._cors()
            self.end_headers()
            self.wfile.write(body)

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/yolo/toggle":
            global yolo_enabled
            yolo_enabled = not yolo_enabled
            camera_status["yolo"] = yolo_enabled
            state = "on" if yolo_enabled else "off"
            print(f"[yolo] Inference {state.upper()}")
            body = json.dumps({"ok": True, "yolo": yolo_enabled}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", len(body))
            self._cors()
            self.end_headers()
            self.wfile.write(body)
            return

        elif self.path == "/reconnect":
            reconnect()
            body = b'{"ok":true}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", len(body))
            self._cors()
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"[server] Starting Veratori Camera Server on port {PORT}")
    # Warm-up: push a loading frame immediately
    try:
        import numpy as np
        blank = np.zeros((FRAME_H, FRAME_W, 3), dtype='uint8')
        cv2.putText(blank, "Loading model and camera…", (10, FRAME_H//2),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (148,163,184), 1, cv2.LINE_AA)
        _, jpg = cv2.imencode('.jpg', blank)
        with lock:
            latest_frame = jpg.tobytes()
    except Exception:
        pass

    # Start capture in background thread
    t = threading.Thread(target=capture_loop, daemon=True)
    t.start()

    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"[server] Ready → http://localhost:{PORT}/stream")
    print(f"[server] Status → http://localhost:{PORT}/status")
    print(f"[server] Reconnect → POST http://localhost:{PORT}/reconnect")

    # Open the dashboard in the default browser after a short warm-up delay
    DASHBOARD_URL = "https://veratori-f3a5a.web.app/"
    def _open_browser():
        time.sleep(2.5)   # let the camera thread start capturing first
        print(f"[server] Opening dashboard → {DASHBOARD_URL}")
        webbrowser.open(DASHBOARD_URL)
    threading.Thread(target=_open_browser, daemon=True).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[server] Stopped.")
