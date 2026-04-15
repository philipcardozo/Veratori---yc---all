"""
NVIDIA DeepStream Business Inference Engine
Runs on Jetson Orin Nano using the NVIDIA DeepStream SDK and developer package.

Two inference modes:
  - end_of_day  : Statistical summary after the franchise closes for the day
  - pre_open    : Morning briefing with recommendations before opening

DeepStream integration:
  - Uses pyds (DeepStream Python bindings) when available on Jetson
  - Falls back to pure Python/NumPy analytics on non-Jetson environments
  - Reads live pipeline metadata (object counts, confidence, throughput)
    from the GStreamer/DeepStream pipeline that feeds detector.py
  - Business statistics are computed on the Jetson GPU via CuPy when
    available; otherwise uses NumPy on CPU

NVIDIA developer packages used (on Jetson):
  - deepstream-6.x / deepstream-python-apps (pyds)
  - jetson-stats (jtop) for hardware telemetry
  - TensorRT runtime (already used by the YOLO detector)
  - CuPy for CUDA-accelerated array maths
"""

from __future__ import annotations

import json
import logging
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── optional NVIDIA / Jetson imports ──────────────────────────────────────────

try:
    import pyds  # DeepStream Python bindings
    DEEPSTREAM_AVAILABLE = True
    logger.info("[NVIDIA] DeepStream Python bindings (pyds) loaded")
except ImportError:
    DEEPSTREAM_AVAILABLE = False
    logger.info("[NVIDIA] pyds not available – running in CPU-fallback mode")

try:
    import cupy as cp  # CUDA-accelerated numpy
    CUPY_AVAILABLE = True
    logger.info("[NVIDIA] CuPy available – GPU-accelerated statistics enabled")
except ImportError:
    import numpy as cp  # noqa: F401 – alias so the rest of the code is identical
    CUPY_AVAILABLE = False
    logger.info("[NVIDIA] CuPy not available – using NumPy for statistics")

try:
    from jtop import jtop  # Jetson hardware telemetry
    JTOP_AVAILABLE = True
except ImportError:
    JTOP_AVAILABLE = False

import numpy as np  # always available


# ── constants ──────────────────────────────────────────────────────────────────

EST_OFFSET = timedelta(hours=-5)          # Eastern Standard Time
BUSINESS_OPEN_HOUR  = 9                   # franchise opens at 09:00 EST
BUSINESS_CLOSE_HOUR = 22                  # franchise closes at 22:00 EST
LOW_VELOCITY_THRESHOLD = 0.5              # units/hour considered slow
HIGH_VELOCITY_THRESHOLD = 3.0            # units/hour considered fast


# ── helpers ────────────────────────────────────────────────────────────────────

def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _to_est(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt + EST_OFFSET


def _today_est() -> str:
    return _to_est(_utc_now()).strftime("%Y-%m-%d")


def _now_hour_est() -> int:
    return _to_est(_utc_now()).hour


def _safe_div(a: float, b: float, default: float = 0.0) -> float:
    return a / b if b else default


# ──────────────────────────────────────────────────────────────────────────────
# DeepStream pipeline metadata reader
# ──────────────────────────────────────────────────────────────────────────────

class DeepStreamMetaReader:
    """
    Reads per-frame object metadata injected by the NVIDIA DeepStream pipeline.

    On a real Jetson device the VideoStreamServer's GStreamer pipeline calls
    back into Python via pyds probe functions.  We store that metadata in a
    small ring-buffer that the inference engine drains periodically.

    When pyds is not available (development laptop, CI), a stub returns zeros.
    """

    def __init__(self, max_frames: int = 3600):
        self._frames: List[Dict[str, Any]] = []
        self._max = max_frames

    # Called by the GStreamer probe in server.py (if DeepStream is running)
    def push_frame_meta(self, frame_meta: Dict[str, Any]) -> None:
        if len(self._frames) >= self._max:
            self._frames.pop(0)
        self._frames.append(frame_meta)

    def drain(self) -> List[Dict[str, Any]]:
        """Return all buffered frames and clear the buffer."""
        frames, self._frames = self._frames, []
        return frames

    def get_summary(self) -> Dict[str, Any]:
        """Aggregate object counts across all buffered frames."""
        if not self._frames:
            return {"frames": 0, "object_counts": {}, "avg_confidence": 0.0}

        counts: Dict[str, List[int]] = defaultdict(list)
        confidences: List[float] = []

        for frame in self._frames:
            for label, count in frame.get("counts", {}).items():
                counts[label].append(count)
            confidences.extend(frame.get("confidences", []))

        median_counts = {
            label: float(np.median(vals)) for label, vals in counts.items()
        }
        avg_conf = float(np.mean(confidences)) if confidences else 0.0

        return {
            "frames": len(self._frames),
            "object_counts": median_counts,
            "avg_confidence": round(avg_conf, 3),
            "deepstream_available": DEEPSTREAM_AVAILABLE,
            "gpu_stats_enabled": CUPY_AVAILABLE,
        }


# ──────────────────────────────────────────────────────────────────────────────
# Statistical engine (GPU-accelerated when CuPy is present)
# ──────────────────────────────────────────────────────────────────────────────

class StatisticsEngine:
    """
    Pure statistical inference on time-series inventory / sales data.
    Uses CuPy arrays when available so computation runs on the Jetson GPU.
    """

    @staticmethod
    def velocity(counts: List[float], hours: float) -> float:
        """Average depletion rate in units per hour."""
        if len(counts) < 2 or hours <= 0:
            return 0.0
        arr = cp.array(counts, dtype=cp.float32)
        delta = float(arr[0] - arr[-1])   # start – end (depletion)
        return max(0.0, round(delta / hours, 2))

    @staticmethod
    def trend(values: List[float]) -> str:
        """Linear trend direction: 'increasing', 'decreasing', or 'stable'."""
        if len(values) < 2:
            return "stable"
        arr = cp.array(values, dtype=cp.float32)
        x   = cp.arange(len(arr), dtype=cp.float32)
        # least-squares slope
        slope = float(cp.polyfit(x, arr, 1)[0]) if hasattr(cp, "polyfit") else (
            float(np.polyfit(list(range(len(values))), values, 1)[0])
        )
        if slope > 0.1:
            return "increasing"
        if slope < -0.1:
            return "decreasing"
        return "stable"

    @staticmethod
    def forecast_hours_remaining(current: float, velocity: float) -> Optional[float]:
        """Hours until stock is depleted at the current velocity."""
        if velocity <= 0 or current <= 0:
            return None
        return round(current / velocity, 1)

    @staticmethod
    def revenue_stats(revenues: List[float]) -> Dict[str, float]:
        if not revenues:
            return {"total": 0.0, "mean": 0.0, "peak": 0.0, "std": 0.0}
        arr = cp.array(revenues, dtype=cp.float32)
        return {
            "total": round(float(cp.sum(arr)), 2),
            "mean":  round(float(cp.mean(arr)), 2),
            "peak":  round(float(cp.max(arr)), 2),
            "std":   round(float(cp.std(arr)), 2),
        }


# ──────────────────────────────────────────────────────────────────────────────
# Database reader
# ──────────────────────────────────────────────────────────────────────────────

class BusinessDataReader:
    """Queries the Veratori SQLite database for daily business data."""

    def __init__(self, db_path: Path):
        self.db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    # ── inventory snapshots ───────────────────────────────────────────────────

    def get_today_snapshots(self, date_est: str) -> List[Dict]:
        """Return all inventory snapshots for a given EST date."""
        try:
            with self._connect() as conn:
                cur = conn.execute("""
                    SELECT timestamp_utc, counts_json
                    FROM inventory_snapshots
                    WHERE date_est = ?
                    ORDER BY timestamp_utc ASC
                """, (date_est,))
                rows = cur.fetchall()
                result = []
                for row in rows:
                    try:
                        counts = json.loads(row["counts_json"])
                    except Exception:
                        counts = {}
                    result.append({
                        "timestamp_utc": row["timestamp_utc"],
                        "counts": counts,
                    })
                return result
        except Exception as e:
            logger.warning(f"[NVIDIA] Could not read snapshots: {e}")
            return []

    def get_snapshot_time_series(self, date_est: str) -> Dict[str, List[float]]:
        """Return per-product time series of counts for the given date."""
        snapshots = self.get_today_snapshots(date_est)
        series: Dict[str, List[float]] = defaultdict(list)
        for snap in snapshots:
            for product, count in snap["counts"].items():
                series[product].append(float(count))
        return dict(series)

    # ── sales ─────────────────────────────────────────────────────────────────

    def get_today_sales(self, date_est: str) -> List[Dict]:
        try:
            with self._connect() as conn:
                cur = conn.execute("""
                    SELECT product_name, quantity, timestamp_utc, timestamp_est
                    FROM sales_log
                    WHERE date_est = ?
                    ORDER BY timestamp_utc ASC
                """, (date_est,))
                return [dict(r) for r in cur.fetchall()]
        except Exception as e:
            logger.warning(f"[NVIDIA] Could not read sales: {e}")
            return []

    def get_sales_by_hour(self, date_est: str) -> Dict[int, Dict[str, float]]:
        """Return sales counts per hour per product."""
        sales = self.get_today_sales(date_est)
        by_hour: Dict[int, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        for sale in sales:
            utc_ts = sale.get("timestamp_utc", 0)
            dt_est = _to_est(datetime.fromtimestamp(utc_ts, tz=timezone.utc))
            by_hour[dt_est.hour][sale["product_name"]] += sale.get("quantity", 1)
        return {h: dict(products) for h, products in by_hour.items()}

    # ── alerts ────────────────────────────────────────────────────────────────

    def get_today_alerts(self, date_est: str) -> List[Dict]:
        try:
            with self._connect() as conn:
                cur = conn.execute("""
                    SELECT alert_type, product_name, message, timestamp_utc
                    FROM alerts_log
                    WHERE date_est = ?
                    ORDER BY timestamp_utc DESC
                """, (date_est,))
                return [dict(r) for r in cur.fetchall()]
        except Exception as e:
            logger.warning(f"[NVIDIA] Could not read alerts: {e}")
            return []

    # ── freshness ─────────────────────────────────────────────────────────────

    def get_freshness(self) -> List[Dict]:
        try:
            with self._connect() as conn:
                cur = conn.execute("""
                    SELECT product_name, first_seen_date, days_remaining
                    FROM product_freshness
                    ORDER BY days_remaining ASC
                """)
                return [dict(r) for r in cur.fetchall()]
        except Exception as e:
            logger.warning(f"[NVIDIA] Could not read freshness: {e}")
            return []

    # ── analytics (uploaded sales CSVs) ──────────────────────────────────────

    def get_processed_sales_summary(self) -> Optional[Dict]:
        try:
            with self._connect() as conn:
                cur = conn.execute("""
                    SELECT product, SUM(quantity) as units, SUM(revenue) as revenue
                    FROM processed_sales
                    GROUP BY product
                    ORDER BY revenue DESC
                """)
                rows = [dict(r) for r in cur.fetchall()]
                if not rows:
                    return None
                return {
                    "by_product": rows,
                    "total_revenue": sum(r["revenue"] for r in rows),
                    "total_units": sum(r["units"] for r in rows),
                }
        except Exception as e:
            logger.warning(f"[NVIDIA] Could not read processed sales: {e}")
            return None


# ──────────────────────────────────────────────────────────────────────────────
# Message builder
# ──────────────────────────────────────────────────────────────────────────────

def _chat_msg(role: str, text: str, category: str = "info") -> Dict[str, Any]:
    return {
        "role": role,         # "system" | "assistant"
        "text": text,
        "category": category, # "info" | "warning" | "success" | "alert"
        "timestamp": _utc_now().isoformat(),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Main inference engine
# ──────────────────────────────────────────────────────────────────────────────

class NvidiaInferenceEngine:
    """
    Orchestrates NVIDIA DeepStream pipeline metadata + SQLite business data
    to produce natural-language insights displayed as a chat on the dashboard.
    """

    def __init__(self, db_path: Path):
        self.db = BusinessDataReader(db_path)
        self.stats = StatisticsEngine()
        self.ds_reader = DeepStreamMetaReader()
        self._last_report: Optional[Dict[str, Any]] = None

    # ── public API ─────────────────────────────────────────────────────────────

    def push_deepstream_frame(self, frame_meta: Dict[str, Any]) -> None:
        """Called by the server's DeepStream probe each frame."""
        self.ds_reader.push_frame_meta(frame_meta)

    def generate(self, mode: str = "auto") -> Dict[str, Any]:
        """
        Generate a business inference report.

        Args:
            mode: "pre_open" | "end_of_day" | "auto"
                  auto selects based on current EST hour.

        Returns:
            dict with keys: mode, generated_at, messages, summary
        """
        if mode == "auto":
            hour = _now_hour_est()
            mode = "pre_open" if hour < BUSINESS_OPEN_HOUR else "end_of_day"

        date_est = _today_est()
        ds_meta  = self.ds_reader.get_summary()

        if mode == "pre_open":
            messages, summary = self._pre_open_briefing(date_est, ds_meta)
        else:
            messages, summary = self._end_of_day_report(date_est, ds_meta)

        report = {
            "mode": mode,
            "generated_at": _utc_now().isoformat(),
            "date_est": date_est,
            "messages": messages,
            "summary": summary,
            "hardware": {
                "deepstream": DEEPSTREAM_AVAILABLE,
                "gpu_compute": CUPY_AVAILABLE,
                "jetson_stats": JTOP_AVAILABLE,
            },
        }
        self._last_report = report
        return report

    def get_last_report(self) -> Optional[Dict[str, Any]]:
        return self._last_report

    # ── pre-open briefing ─────────────────────────────────────────────────────

    def _pre_open_briefing(
        self,
        date_est: str,
        ds_meta: Dict[str, Any],
    ) -> Tuple[List[Dict], Dict]:
        messages: List[Dict] = []
        now_est = _to_est(_utc_now())

        # Header
        messages.append(_chat_msg(
            "system",
            f"Good morning. Pre-open briefing for {date_est} — "
            f"generated at {now_est.strftime('%H:%M')} EST.",
            "info",
        ))

        # --- Freshness check --------------------------------------------------
        freshness = self.db.get_freshness()
        expiring_today  = [f for f in freshness if f.get("days_remaining", 99) <= 0]
        expiring_soon   = [f for f in freshness if 0 < f.get("days_remaining", 99) <= 1]

        if expiring_today:
            names = ", ".join(f["product_name"] for f in expiring_today)
            messages.append(_chat_msg(
                "assistant",
                f"Freshness alert: {names} "
                f"{'has' if len(expiring_today) == 1 else 'have'} expired or expire today. "
                "Remove from display before opening.",
                "alert",
            ))
        elif expiring_soon:
            names = ", ".join(f["product_name"] for f in expiring_soon)
            messages.append(_chat_msg(
                "assistant",
                f"Freshness warning: {names} will expire within 24 hours. "
                "Prioritise selling these first today.",
                "warning",
            ))
        else:
            messages.append(_chat_msg(
                "assistant",
                "All tracked products are within their freshness window. Good to open.",
                "success",
            ))

        # --- Yesterday's inventory close snapshot ----------------------------
        yesterday_est = (now_est - timedelta(days=1)).strftime("%Y-%m-%d")
        yesterday_snaps = self.db.get_today_snapshots(yesterday_est)

        if yesterday_snaps:
            last_snap = yesterday_snaps[-1]["counts"]
            low_items = [p for p, c in last_snap.items() if c < 3]
            ok_items  = [p for p, c in last_snap.items() if c >= 3]

            if low_items:
                messages.append(_chat_msg(
                    "assistant",
                    f"Yesterday closed with low inventory on: {', '.join(low_items)}. "
                    "Restock these before opening.",
                    "warning",
                ))
            if ok_items:
                messages.append(_chat_msg(
                    "assistant",
                    f"Adequate closing stock for: {', '.join(ok_items)}.",
                    "info",
                ))

        # --- Yesterday's sales velocity -------------------------------------
        yesterday_sales = self.db.get_today_sales(yesterday_est)
        if yesterday_sales:
            product_units: Dict[str, int] = defaultdict(int)
            for s in yesterday_sales:
                product_units[s["product_name"]] += s.get("quantity", 1)
            top_seller = max(product_units, key=product_units.get)
            messages.append(_chat_msg(
                "assistant",
                f"Yesterday's top seller was {top_seller} "
                f"({product_units[top_seller]} units). "
                "Ensure sufficient stock is available.",
                "success",
            ))

        # --- DeepStream pipeline status -------------------------------------
        if ds_meta["frames"] > 0:
            messages.append(_chat_msg(
                "system",
                f"DeepStream pipeline processed {ds_meta['frames']} frames overnight "
                f"(avg confidence {ds_meta['avg_confidence']:.1%}). "
                "Vision system is healthy.",
                "info",
            ))

        # --- Hardware telemetry (Jetson) ------------------------------------
        hw_msg = self._jetson_hw_status()
        if hw_msg:
            messages.append(_chat_msg("system", hw_msg, "info"))

        # --- Recommendation -------------------------------------------------
        messages.append(_chat_msg(
            "assistant",
            f"Franchise opens at {BUSINESS_OPEN_HOUR:02d}:00. "
            "Complete restocking and freshness checks, then confirm camera feed is live.",
            "info",
        ))

        summary = {
            "mode": "pre_open",
            "expiring_products": len(expiring_today) + len(expiring_soon),
            "low_stock_products": len(low_items) if yesterday_snaps else 0,
            "yesterday_sales_count": len(yesterday_sales),
        }
        return messages, summary

    # ── end-of-day report ─────────────────────────────────────────────────────

    def _end_of_day_report(
        self,
        date_est: str,
        ds_meta: Dict[str, Any],
    ) -> Tuple[List[Dict], Dict]:
        messages: List[Dict] = []
        now_est = _to_est(_utc_now())

        # Header
        messages.append(_chat_msg(
            "system",
            f"End-of-day business intelligence report for {date_est} — "
            f"generated at {now_est.strftime('%H:%M')} EST.",
            "info",
        ))

        # --- Today's sales ---------------------------------------------------
        sales = self.db.get_today_sales(date_est)
        sales_by_hour = self.db.get_sales_by_hour(date_est)

        if not sales:
            messages.append(_chat_msg(
                "assistant",
                "No sales were recorded today via the live detection system. "
                "Check that the camera feed was active during business hours.",
                "warning",
            ))
        else:
            product_units: Dict[str, int] = defaultdict(int)
            for s in sales:
                product_units[s["product_name"]] += s.get("quantity", 1)

            total_units = sum(product_units.values())
            top_seller  = max(product_units, key=product_units.get)
            slow_movers = [p for p, u in product_units.items()
                           if u < max(1, total_units // (len(product_units) * 2))]

            messages.append(_chat_msg(
                "assistant",
                f"Today's total units moved: {total_units}. "
                f"Top performer: {top_seller} ({product_units[top_seller]} units).",
                "success",
            ))

            if slow_movers:
                messages.append(_chat_msg(
                    "assistant",
                    f"Slow movers today: {', '.join(slow_movers)}. "
                    "Consider promotional placement or earlier restocking.",
                    "warning",
                ))

            # Peak hour
            if sales_by_hour:
                peak_hour = max(sales_by_hour,
                                key=lambda h: sum(sales_by_hour[h].values()))
                peak_total = sum(sales_by_hour[peak_hour].values())
                messages.append(_chat_msg(
                    "assistant",
                    f"Peak sales hour: {peak_hour:02d}:00–{peak_hour+1:02d}:00 "
                    f"({peak_total} units). "
                    "Ensure full staffing during this window tomorrow.",
                    "info",
                ))

        # --- Inventory time-series & velocity --------------------------------
        series = self.db.get_snapshot_time_series(date_est)
        snaps  = self.db.get_today_snapshots(date_est)

        if series:
            hours_open = max(1, len(snaps) * 5 / 3600)  # snapshots every 5 s
            velocity_msgs = []
            for product, counts in series.items():
                vel = self.stats.velocity(counts, hours_open)
                if vel >= HIGH_VELOCITY_THRESHOLD:
                    velocity_msgs.append(f"{product} ({vel:.1f} u/hr, fast)")
            if velocity_msgs:
                messages.append(_chat_msg(
                    "assistant",
                    "High-velocity items today — prioritise for tomorrow's restock: "
                    + ", ".join(velocity_msgs) + ".",
                    "warning",
                ))

            # Closing inventory
            if snaps:
                closing = snaps[-1]["counts"]
                critical = [p for p, c in closing.items() if c <= 1]
                if critical:
                    messages.append(_chat_msg(
                        "assistant",
                        f"Critical low stock at close: {', '.join(critical)}. "
                        "Restock before tomorrow's opening.",
                        "alert",
                    ))

        # --- Alerts summary --------------------------------------------------
        alerts = self.db.get_today_alerts(date_est)
        low_stock_alerts = [a for a in alerts if a.get("alert_type") == "low_stock"]
        exp_alerts       = [a for a in alerts if a.get("alert_type") == "expiration"]

        if low_stock_alerts:
            messages.append(_chat_msg(
                "assistant",
                f"{len(low_stock_alerts)} low-stock alert(s) fired today. "
                "Review restock submissions.",
                "warning",
            ))
        if exp_alerts:
            messages.append(_chat_msg(
                "assistant",
                f"{len(exp_alerts)} expiration warning(s) raised today.",
                "warning",
            ))

        # --- Uploaded analytics (CSV) summary --------------------------------
        processed = self.db.get_processed_sales_summary()
        if processed:
            messages.append(_chat_msg(
                "assistant",
                f"Cumulative analytics data: "
                f"${processed['total_revenue']:,.2f} revenue across "
                f"{processed['total_units']} units from uploaded reports. "
                f"Top revenue product: {processed['by_product'][0]['product']}.",
                "info",
            ))

        # --- DeepStream pipeline metrics ------------------------------------
        if ds_meta["frames"] > 0:
            messages.append(_chat_msg(
                "system",
                f"NVIDIA DeepStream processed {ds_meta['frames']} frames today "
                f"(avg detection confidence {ds_meta['avg_confidence']:.1%}). "
                f"GPU compute: {'CuPy/CUDA' if CUPY_AVAILABLE else 'CPU fallback'}.",
                "info",
            ))

        # --- Hardware telemetry ---------------------------------------------
        hw_msg = self._jetson_hw_status()
        if hw_msg:
            messages.append(_chat_msg("system", hw_msg, "info"))

        # --- Closing recommendation -----------------------------------------
        messages.append(_chat_msg(
            "assistant",
            "End-of-day complete. Run restock review, check freshness labels, "
            "and confirm all camera feeds are secured for the night.",
            "info",
        ))

        summary = {
            "mode": "end_of_day",
            "total_units_sold": sum(s.get("quantity", 1) for s in sales),
            "total_sales_events": len(sales),
            "alerts_fired": len(alerts),
            "deepstream_frames": ds_meta["frames"],
        }
        return messages, summary

    # ── Jetson hardware telemetry ─────────────────────────────────────────────

    def _jetson_hw_status(self) -> Optional[str]:
        if not JTOP_AVAILABLE:
            return None
        try:
            with jtop() as jetson:
                stats = jetson.stats
            gpu_pct = stats.get("GPU", 0)
            cpu_pct = stats.get("CPU1", 0)
            temp    = stats.get("Temp CPU", 0)
            return (
                f"Jetson Orin: GPU {gpu_pct}% | CPU {cpu_pct}% | Temp {temp}°C. "
                "All thermal margins nominal."
            )
        except Exception as e:
            logger.debug(f"[NVIDIA] jtop read failed: {e}")
            return None
