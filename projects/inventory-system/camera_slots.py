"""
Multi-camera slot manager for the Veratori camera server.

Up to 4 slots, each owning one physical camera + its own YOLO model instance +
its own SalesTracker. Slot 0 is the primary (legacy) slot — endpoints with no
?camera= param default to it. Slot assignments persist to slots.json so a
restart preserves which physical camera is in which slot.

Why one YOLO model per slot: ByteTrack maintains internal state inside the
model object (track IDs, lost-track buffers). Sharing one model across 4
camera streams would cross-contaminate IDs. yolov8n is ~24 MB resident; 4
instances = ~100 MB, well within budget.
"""

from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from dataclasses import dataclass, field
from typing import Optional

import cv2
import numpy as np
from ultralytics import YOLO

from sales_tracker import SalesTracker, is_food_drink


MAX_SLOTS  = 4
FRAME_W    = 640
FRAME_H    = 480
INFER_SIZE = 416
INFER_EVERY = 2
CONF_THRESH = 0.40

PALETTE = [
    (16,185,129), (59,130,246), (245,158,11), (239,68,68),
    (139,92,246), (236,72,153), (14,165,233), (34,197,94),
    (251,146,60), (99,102,241),
]

_PHONE_KEYWORDS   = ["iphone", "ipad", "android", "continuity", "droidcam",
                     "epoccam", "camo", "ndccam", "obs virtual", "mmhmm"]
_BUILTIN_KEYWORDS = ["facetime", "built-in", "builtin", "integrated", "isight"]


def _scan_cameras():
    """Return ranked list of {idx, name, tier} for all macOS cameras."""
    try:
        result = subprocess.run(
            ["system_profiler", "SPCameraDataType", "-json"],
            capture_output=True, text=True, timeout=5,
        )
        cameras = json.loads(result.stdout).get("SPCameraDataType", [])
        if cameras:
            ranked = []
            for i, cam in enumerate(cameras):
                name = cam.get("_name", f"Camera {i}")
                nl   = name.lower()
                if any(k in nl for k in _PHONE_KEYWORDS):
                    tier = 2
                elif any(k in nl for k in _BUILTIN_KEYWORDS):
                    tier = 1
                else:
                    tier = 0
                ranked.append({"idx": i, "name": name, "tier": tier})
            ranked.sort(key=lambda r: (r["tier"], r["idx"]))
            return ranked
    except Exception as e:
        print(f"[slots] system_profiler scan failed: {e}")
    return [{"idx": i, "name": f"index {i}", "tier": 1} for i in range(4)]


def _try_open(idx: int, name: str) -> Optional[cv2.VideoCapture]:
    """Open camera at idx and confirm it produces live frames."""
    cap = cv2.VideoCapture(idx, cv2.CAP_AVFOUNDATION)
    if not cap.isOpened():
        cap.release()
        return None
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  FRAME_W)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_H)
    for _ in range(5):
        ok, frame = cap.read()
        if ok and frame is not None:
            print(f"[slots] ✓ Live frames from '{name}' (index {idx})")
            return cap
    print(f"[slots] ✗ '{name}' (index {idx}) opened but no frames")
    cap.release()
    return None


@dataclass
class CameraSlot:
    slot_id:        int
    sales_dir:      str
    model_path:     str
    camera_idx:     Optional[int] = None
    camera_name:    str = ""
    cap:            Optional[cv2.VideoCapture] = None
    model:          Optional[YOLO] = None
    sales_tracker:  Optional[SalesTracker] = None
    yolo_enabled:   bool = False
    latest_frame:   Optional[bytes] = None
    latest_detections: list = field(default_factory=list)
    last_drawable_boxes: list = field(default_factory=list)
    status:         dict = field(default_factory=lambda: {"connected": False, "error": None, "fps": 0, "yolo": False})
    thread:         Optional[threading.Thread] = None
    stop_event:     threading.Event = field(default_factory=threading.Event)
    lock:           threading.Lock = field(default_factory=threading.Lock)

    def is_active(self) -> bool:
        return self.camera_idx is not None

    def configure(self, camera_idx: Optional[int], camera_name: str = ""):
        """
        Assign (or clear) a physical camera on this slot. Safe to call while
        the slot's capture thread is running — it signals stop, joins, then
        spins up a fresh thread bound to the new camera.
        """
        # Stop existing thread cleanly
        if self.thread and self.thread.is_alive():
            self.stop_event.set()
            self.thread.join(timeout=3)
        self.stop_event = threading.Event()

        # Release the previous capture if any
        if self.cap is not None:
            try: self.cap.release()
            except Exception: pass
            self.cap = None

        self.camera_idx  = camera_idx
        self.camera_name = camera_name
        self.latest_frame = None
        self.latest_detections = []
        self.last_drawable_boxes = []

        if camera_idx is None:
            self.status = {"connected": False, "error": None, "fps": 0, "yolo": False}
            return

        # Lazy-load model + tracker once per slot
        if self.model is None:
            print(f"[slot {self.slot_id}] loading YOLO model…")
            self.model = YOLO(self.model_path)
        if self.sales_tracker is None:
            self.sales_tracker = SalesTracker(self.sales_dir, camera_id=self.slot_id)

        self.thread = threading.Thread(target=self._capture_loop, daemon=True, name=f"slot-{self.slot_id}")
        self.thread.start()

    def _capture_loop(self):
        """Per-slot capture + inference loop. Mirrors the original camera_server logic."""
        cap = _try_open(self.camera_idx, self.camera_name or f"slot {self.slot_id}")
        if cap is None:
            self.status = {"connected": False, "error": f"Could not open camera {self.camera_idx}", "fps": 0, "yolo": False}
            self._serve_error_frame()
            return
        self.cap = cap
        self.status = {"connected": True, "error": None, "fps": 0, "yolo": self.yolo_enabled}

        t0 = time.time()
        fc = 0
        frame_idx = 0

        while not self.stop_event.is_set():
            ok, frame = cap.read()
            if not ok:
                self.status["connected"] = False
                self.status["error"] = "Frame read failed"
                time.sleep(0.5)
                continue

            if self.yolo_enabled and self.model is not None:
                if frame_idx % INFER_EVERY == 0:
                    try:
                        if INFER_SIZE != FRAME_W or INFER_SIZE != FRAME_H:
                            infer_frame = cv2.resize(frame, (INFER_SIZE, INFER_SIZE))
                            sx, sy = FRAME_W / INFER_SIZE, FRAME_H / INFER_SIZE
                        else:
                            infer_frame, sx, sy = frame, 1.0, 1.0

                        results = self.model.track(infer_frame, conf=CONF_THRESH, persist=True, verbose=False)
                        tracker_input, counts, drawable = [], {}, []
                        for r in results:
                            for box in r.boxes:
                                x1, y1, x2, y2 = box.xyxy[0]
                                x1 = int(x1 * sx); y1 = int(y1 * sy)
                                x2 = int(x2 * sx); y2 = int(y2 * sy)
                                cls   = int(box.cls[0])
                                conf  = float(box.conf[0])
                                label = self.model.names[cls] if hasattr(self.model, "names") else str(cls)
                                tid   = int(box.id[0]) if box.id is not None else None
                                drawable.append((x1, y1, x2, y2, cls, conf, label))
                                if tid is not None and is_food_drink(label):
                                    tracker_input.append({"track_id": tid, "label": label, "conf": conf})
                                if is_food_drink(label):
                                    row = counts.setdefault(label, {"label": label, "count": 0, "conf": 0.0})
                                    row["count"] += 1
                                    row["conf"] = max(row["conf"], conf)
                        self.last_drawable_boxes = drawable
                        self.sales_tracker.update(tracker_input)
                        with self.lock:
                            self.latest_detections = sorted(counts.values(), key=lambda x: -x["count"])
                    except Exception as e:
                        print(f"[slot {self.slot_id}] inference error: {e}")
                # Draw last-known boxes on every frame so the stream stays smooth
                self._draw(frame, self.last_drawable_boxes)
            else:
                with self.lock:
                    self.latest_detections = []
                self.last_drawable_boxes = []
                if self.sales_tracker is not None:
                    self.sales_tracker.update([])

            frame_idx += 1
            fc += 1
            elapsed = time.time() - t0
            if elapsed >= 1.0:
                self.status["fps"]  = round(fc / elapsed, 1)
                self.status["yolo"] = self.yolo_enabled
                fc = 0; t0 = time.time()

            _, jpg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 82])
            with self.lock:
                self.latest_frame = jpg.tobytes()

        try: cap.release()
        except Exception: pass
        self.cap = None

    def _draw(self, frame, boxes_list):
        for box in boxes_list:
            x1, y1, x2, y2, cls, conf, label = box
            color = PALETTE[cls % len(PALETTE)]
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            text = f"{label}  {conf:.0%}"
            (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            cv2.rectangle(frame, (x1, y1 - th - 6), (x1 + tw + 6, y1), color, -1)
            cv2.putText(frame, text, (x1 + 3, y1 - 3),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

    def _serve_error_frame(self):
        blank = np.zeros((FRAME_H, FRAME_W, 3), dtype="uint8")
        cv2.putText(blank, self.status.get("error", "No camera"), (10, FRAME_H // 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (239, 68, 68), 1, cv2.LINE_AA)
        cv2.putText(blank, f"Slot {self.slot_id} — click Rescan", (10, FRAME_H // 2 + 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (148, 163, 184), 1, cv2.LINE_AA)
        _, jpg = cv2.imencode(".jpg", blank)
        with self.lock:
            self.latest_frame = jpg.tobytes()


class SlotManager:
    def __init__(self, sales_dir: str, model_path: str, slots_config_path: str):
        self.sales_dir   = sales_dir
        self.model_path  = model_path
        self.config_path = slots_config_path
        self.slots = [
            CameraSlot(slot_id=i, sales_dir=sales_dir, model_path=model_path)
            for i in range(MAX_SLOTS)
        ]
        self.available_cameras: list = []

    def auto_assign(self):
        """Scan available cameras, assign one per slot in tier-priority order."""
        ranked = _scan_cameras()
        self.available_cameras = ranked
        used = self._load_persisted()

        # Apply persisted mapping first
        for slot in self.slots:
            persisted_idx = used.get(slot.slot_id)
            if persisted_idx is not None:
                cam = next((c for c in ranked if c["idx"] == persisted_idx), None)
                if cam:
                    slot.configure(cam["idx"], cam["name"])

        # Then auto-fill any unassigned slots from remaining cameras
        taken = {s.camera_idx for s in self.slots if s.is_active()}
        free  = [c for c in ranked if c["idx"] not in taken]
        for slot in self.slots:
            if slot.is_active() or not free:
                continue
            cam = free.pop(0)
            slot.configure(cam["idx"], cam["name"])

        self._save_persisted()
        active = [(s.slot_id, s.camera_name) for s in self.slots if s.is_active()]
        print(f"[slots] assignment: {active}")

    def rescan(self):
        """Re-query the OS for newly plugged-in / removed cameras."""
        ranked = _scan_cameras()
        self.available_cameras = ranked
        return ranked

    def assign(self, slot_id: int, camera_idx: Optional[int]):
        if not 0 <= slot_id < MAX_SLOTS:
            raise ValueError(f"slot_id out of range: {slot_id}")
        cam = next((c for c in self.available_cameras if c["idx"] == camera_idx), None) if camera_idx is not None else None
        name = cam["name"] if cam else ""
        self.slots[slot_id].configure(camera_idx, name)
        self._save_persisted()

    def toggle_yolo(self, slot_id: Optional[int] = None) -> dict:
        """Toggle YOLO on a specific slot, or on ALL active slots if slot_id is None."""
        if slot_id is None:
            # Use slot 0 as the leader — toggle it, then sync the rest
            new_state = not self.slots[0].yolo_enabled
            for slot in self.slots:
                if slot.is_active():
                    slot.yolo_enabled = new_state
                    slot.status["yolo"] = new_state
            return {"ok": True, "yolo": new_state, "applied_to": [s.slot_id for s in self.slots if s.is_active()]}
        slot = self.slots[slot_id]
        slot.yolo_enabled = not slot.yolo_enabled
        slot.status["yolo"] = slot.yolo_enabled
        return {"ok": True, "yolo": slot.yolo_enabled, "slot": slot_id}

    def slots_snapshot(self) -> list:
        return [{
            "slot":        s.slot_id,
            "camera_idx":  s.camera_idx,
            "camera_name": s.camera_name,
            "active":      s.is_active(),
            "status":      dict(s.status),
        } for s in self.slots]

    # ── Aggregation helpers across slots ──────────────────────────────────────
    def aggregated_sales_summary(self) -> dict:
        """Sum of today's totals across all active slots + merged recent feed."""
        date    = None
        count   = 0
        revenue = 0.0
        recent  = []
        for s in self.slots:
            if not s.is_active() or s.sales_tracker is None:
                continue
            summary = s.sales_tracker.get_sales_summary()
            t = summary["today"]
            date = t["date"]
            count   += t["count"]
            revenue += t["revenue_usd"]
            for entry in summary["recent"]:
                entry = dict(entry); entry["slot"] = s.slot_id
                recent.append(entry)
        recent.sort(key=lambda r: r.get("time", 0), reverse=True)
        return {"today": {"date": date, "count": count, "revenue_usd": revenue}, "recent": recent[:20]}

    def aggregated_inventory(self) -> list:
        merged = {}
        for s in self.slots:
            if not s.is_active() or s.sales_tracker is None:
                continue
            for row in s.sales_tracker.get_inventory():
                key = row["label"]
                cur = merged.setdefault(key, dict(row))
                if cur is not row:
                    cur["count"] += row["count"]
                    cur["oldest_display_seconds"] = max(cur["oldest_display_seconds"], row["oldest_display_seconds"])
                    cur["expiring"] = cur["expiring"] or row["expiring"]
        return sorted(merged.values(), key=lambda r: -r["count"])

    def aggregated_alerts(self) -> list:
        out = []
        for s in self.slots:
            if not s.is_active() or s.sales_tracker is None:
                continue
            for a in s.sales_tracker.get_alerts():
                a = dict(a); a["slot"] = s.slot_id; a["camera_name"] = s.camera_name
                out.append(a)
        return out

    # ── Persistence ───────────────────────────────────────────────────────────
    def _load_persisted(self) -> dict:
        if not os.path.exists(self.config_path):
            return {}
        try:
            with open(self.config_path) as f:
                data = json.load(f)
            return {int(k): v for k, v in data.get("slots", {}).items() if v is not None}
        except Exception as e:
            print(f"[slots] could not load {self.config_path}: {e}")
            return {}

    def _save_persisted(self):
        try:
            data = {"slots": {s.slot_id: s.camera_idx for s in self.slots}}
            with open(self.config_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[slots] could not save {self.config_path}: {e}")
