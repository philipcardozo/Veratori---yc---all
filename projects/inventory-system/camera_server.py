"""
Veratori multi-camera server.

Manages up to 4 camera slots, each running its own YOLO model + SalesTracker.
HTTP layer routes requests by ?camera=<slot> query param; missing param
defaults to slot 0 for backwards-compat with the single-cam endpoints
already wired into the frontend.

Endpoints:
  GET  /stream?camera=N          MJPEG stream from slot N (default 0)
  GET  /snapshot?camera=N        Single JPEG from slot N
  GET  /status?camera=N          Slot health
  GET  /cameras                  All detected cams + ranked tiers (?refresh=1 forces rescan)
  GET  /slots                    Current slot → camera assignment
  POST /slots/{N}/assign         body: {"camera_idx": <int|null>}
  GET  /detections?camera=N      Per-slot detections (no param = slot 0)
  GET  /inventory                Aggregated across all slots
  GET  /inventory?camera=N       One slot
  GET  /sales                    Aggregated totals + merged recent feed
  GET  /sales?camera=N           One slot
  GET  /alerts                   Aggregated freshness alerts
  GET  /report?...               Weekly aggregation JSON (existing)
  GET  /report.docx?...          Weekly report download (existing)
  GET  /report.pdf?...           Weekly report PDF (existing)
  POST /yolo/toggle              Toggle inference on all active slots
  POST /yolo/toggle?camera=N     Toggle inference on one slot
  POST /reconnect?camera=N       Re-init a slot's capture
  POST /camera/select            Legacy: body {"index": <cam_idx>} re-assigns slot 0
"""

import json
import os
import threading
import time
import webbrowser
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler
from socketserver import ThreadingMixIn, TCPServer
from urllib.parse import urlparse, parse_qs

from camera_slots import SlotManager, MAX_SLOTS
import report_builder


class ThreadingHTTPServer(ThreadingMixIn, TCPServer):
    allow_reuse_address = True
    daemon_threads      = True


PORT      = 5001
_MODEL_DIR  = os.path.join(os.path.dirname(__file__), "models")
MODEL_PATH  = (
    os.path.join(_MODEL_DIR, "yolov8n.engine")
    if os.path.exists(os.path.join(_MODEL_DIR, "yolov8n.engine"))
    else os.path.join(_MODEL_DIR, "yolov8n.pt")
)
SALES_DIR   = os.path.join(os.path.dirname(__file__), "sales")
SLOTS_CONFIG = os.path.join(os.path.dirname(__file__), "slots.json")

slots: SlotManager = SlotManager(SALES_DIR, MODEL_PATH, SLOTS_CONFIG)


def _slot_id_from_query(q: dict, default: int = 0) -> int:
    """Extract ?camera=N from a parsed query dict, clamped to [0, MAX_SLOTS-1]."""
    raw = (q.get("camera") or [str(default)])[0]
    try:
        n = int(raw)
    except (TypeError, ValueError):
        n = default
    return max(0, min(MAX_SLOTS - 1, n))


def _json_response(handler, status, payload):
    body = json.dumps(payload).encode()
    handler.send_response(status)
    handler.send_header("Content-Type",   "application/json")
    handler.send_header("Content-Length", len(body))
    handler.send_header("Cache-Control",  "no-cache, no-store")
    handler._cors()
    handler.end_headers()
    handler.wfile.write(body)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    # Origins allowed to make credentialed cross-origin requests. Wildcard
    # Allow-Origin is incompatible with Allow-Credentials: true, so we echo
    # back the request's Origin only when it matches this allow-list. Anything
    # else gets no CORS headers (browser blocks the request — fail-closed).
    _ALLOWED_ORIGINS = {
        "https://veratori-f3a5a.web.app",
        "https://veratori-f3a5a.firebaseapp.com",
        "http://localhost:5001",
        "http://localhost:3000",
        "http://127.0.0.1:5001",
    }

    def _cors(self):
        origin = self.headers.get("Origin", "")
        if origin in self._ALLOWED_ORIGINS:
            self.send_header("Access-Control-Allow-Origin",      origin)
            self.send_header("Access-Control-Allow-Credentials", "true")
            self.send_header("Vary",                             "Origin")
        else:
            # No Origin header (server-to-server or curl) — allow but no cookies.
            self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def do_OPTIONS(self):
        self.send_response(200); self._cors(); self.end_headers()

    # ── GET ──────────────────────────────────────────────────────────────────
    def do_GET(self):
        parsed = urlparse(self.path)
        q      = parse_qs(parsed.query)
        path   = parsed.path

        if path == "/stream":
            slot = slots.slots[_slot_id_from_query(q)]
            self.send_response(200)
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
            self._cors(); self.end_headers()
            try:
                while True:
                    with slot.lock:
                        frame = slot.latest_frame
                    if frame:
                        self.wfile.write(b"--frame\r\n")
                        self.wfile.write(b"Content-Type: image/jpeg\r\n\r\n")
                        self.wfile.write(frame)
                        self.wfile.write(b"\r\n")
                        self.wfile.flush()
                    time.sleep(0.033)
            except (BrokenPipeError, ConnectionResetError):
                pass

        elif path == "/snapshot":
            slot = slots.slots[_slot_id_from_query(q)]
            with slot.lock:
                frame = slot.latest_frame
            if frame:
                self.send_response(200)
                self.send_header("Content-Type",   "image/jpeg")
                self.send_header("Content-Length", len(frame))
                self.send_header("Cache-Control",  "no-cache, no-store")
                self._cors(); self.end_headers()
                self.wfile.write(frame)
            else:
                self.send_response(503); self._cors(); self.end_headers()

        elif path == "/status":
            slot = slots.slots[_slot_id_from_query(q)]
            _json_response(self, 200, slot.status)

        elif path == "/cameras":
            if q.get("refresh") == ["1"] or "refresh=1" in parsed.query:
                slots.rescan()
            _json_response(self, 200, {
                "cameras":      list(slots.available_cameras),
                "active_index": slots.slots[0].camera_idx,  # legacy single-cam field
            })

        elif path == "/slots":
            _json_response(self, 200, {"slots": slots.slots_snapshot()})

        elif path == "/detections":
            slot = slots.slots[_slot_id_from_query(q)]
            with slot.lock:
                payload = list(slot.latest_detections)
            _json_response(self, 200, payload)

        elif path == "/inventory":
            if "camera" in q:
                slot = slots.slots[_slot_id_from_query(q)]
                payload = slot.sales_tracker.get_inventory() if slot.sales_tracker else []
            else:
                payload = slots.aggregated_inventory()
            _json_response(self, 200, payload)

        elif path == "/sales":
            if "camera" in q:
                slot = slots.slots[_slot_id_from_query(q)]
                payload = slot.sales_tracker.get_sales_summary() if slot.sales_tracker else \
                          {"today": {"date": None, "count": 0, "revenue_usd": 0.0}, "recent": []}
            else:
                payload = slots.aggregated_sales_summary()
            _json_response(self, 200, payload)

        elif path == "/alerts":
            _json_response(self, 200, slots.aggregated_alerts())

        elif path == "/report" or (path.startswith("/report") and not path.endswith(".docx") and not path.endswith(".pdf")):
            # JSON aggregation for the dashboard reporting card.
            end    = (q.get("end")    or [datetime.now().strftime("%Y-%m-%d")])[0]
            period = (q.get("period") or [""])[0]
            start  = (q.get("start")  or [""])[0]
            if not start:
                try:
                    end_dt = datetime.strptime(end, "%Y-%m-%d")
                except ValueError:
                    end_dt = datetime.now()
                    end    = end_dt.strftime("%Y-%m-%d")
                back  = 29 if period == "monthly" else 6
                start = (end_dt - timedelta(days=back)).strftime("%Y-%m-%d")
            tracker = slots.slots[0].sales_tracker
            payload = tracker.get_report(start, end) if tracker else None
            if payload is None:
                _json_response(self, 400, {"error": "bad date format or no tracker"})
            else:
                _json_response(self, 200, payload)

        elif path == "/report.docx" or path == "/report.pdf":
            want_pdf  = path.endswith(".pdf")
            franchise = (q.get("franchise") or ["cam"])[0]
            week      = (q.get("week")      or [""])[0]
            if not week:
                from datetime import date as _d
                yr, wk, _ = _d.today().isocalendar()
                week = f"{yr}-W{wk:02d}"
            tracker = slots.slots[0].sales_tracker
            try:
                docx_bytes = report_builder.build_report(franchise, week, tracker)
                if want_pdf:
                    payload = report_builder.docx_bytes_to_pdf_bytes(docx_bytes)
                    mime, ext = "application/pdf", "pdf"
                else:
                    payload, mime, ext = docx_bytes, \
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "docx"
            except Exception as e:
                print(f"[report] generation failed: {e}")
                _json_response(self, 500, {"error": str(e)}); return
            fname = f"Veratori_Weekly_Report_{franchise}_{week}.{ext}"
            self.send_response(200)
            self.send_header("Content-Type",        mime)
            self.send_header("Content-Length",      len(payload))
            self.send_header("Content-Disposition", f'attachment; filename="{fname}"')
            self.send_header("Cache-Control",       "no-cache, no-store")
            self._cors(); self.end_headers()
            self.wfile.write(payload)

        else:
            self.send_response(404); self.end_headers()

    # ── POST ─────────────────────────────────────────────────────────────────
    def do_POST(self):
        parsed = urlparse(self.path)
        q      = parse_qs(parsed.query)
        path   = parsed.path

        if path == "/yolo/toggle":
            slot_id = _slot_id_from_query(q, default=-1) if "camera" in q else None
            result = slots.toggle_yolo(slot_id if slot_id is not None and slot_id >= 0 else None)
            _json_response(self, 200, result)
            return

        if path == "/camera/select":
            # Legacy single-cam path: re-assigns slot 0.
            length = int(self.headers.get("Content-Length") or 0)
            try:
                data = json.loads(self.rfile.read(length) or b"{}")
                idx  = int(data.get("index"))
            except Exception as e:
                _json_response(self, 400, {"ok": False, "error": f"bad request: {e}"}); return
            slots.assign(0, idx)
            _json_response(self, 200, {"ok": True, "slot": 0, "camera_idx": idx})
            return

        # POST /slots/{N}/assign  body: {"camera_idx": <int|null>}
        if path.startswith("/slots/") and path.endswith("/assign"):
            try:
                slot_id = int(path.split("/")[2])
            except (ValueError, IndexError):
                _json_response(self, 400, {"ok": False, "error": "bad slot id"}); return
            length = int(self.headers.get("Content-Length") or 0)
            try:
                data = json.loads(self.rfile.read(length) or b"{}")
                cam_idx = data.get("camera_idx")
                if cam_idx is not None:
                    cam_idx = int(cam_idx)
            except Exception as e:
                _json_response(self, 400, {"ok": False, "error": f"bad request: {e}"}); return
            try:
                slots.assign(slot_id, cam_idx)
            except ValueError as e:
                _json_response(self, 400, {"ok": False, "error": str(e)}); return
            _json_response(self, 200, {"ok": True, "slot": slot_id, "camera_idx": cam_idx})
            return

        if path == "/reconnect":
            slot_id = _slot_id_from_query(q) if "camera" in q else 0
            slot = slots.slots[slot_id]
            slot.configure(slot.camera_idx, slot.camera_name)
            _json_response(self, 200, {"ok": True, "slot": slot_id})
            return

        self.send_response(404); self.end_headers()


if __name__ == "__main__":
    print(f"[server] Starting Veratori multi-cam server on port {PORT}")
    slots.auto_assign()

    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"[server] Ready → http://localhost:{PORT}/stream?camera=0")
    print(f"[server] Slots → http://localhost:{PORT}/slots")

    DASHBOARD_URL = "https://veratori-f3a5a.web.app/"
    def _open_browser():
        time.sleep(2.5)
        print(f"[server] Opening dashboard → {DASHBOARD_URL}")
        webbrowser.open(DASHBOARD_URL)
    threading.Thread(target=_open_browser, daemon=True).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[server] Stopped.")
