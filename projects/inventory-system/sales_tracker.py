"""
Veratori sales tracker — 5-second protocol for inventory + sales detection.

State machine per tracked item (track_id from YOLOv8 tracker):
  NEW          (just appeared)
   │  visible for >= APPEARANCE_THRESHOLD_S
   ▼
  IN_DISPLAY   (counted as on the shelf, freshness timer running)
   │  not seen for >= DISAPPEARANCE_THRESHOLD_S
   ▼
  SOLD         (one row appended to today's CSV)
"""

import csv
import os
import threading
import time
from datetime import datetime, timedelta

# ── Config ────────────────────────────────────────────────────────────────────
APPEARANCE_THRESHOLD_S    = 5.0   # must be visible this long before counting
DISAPPEARANCE_THRESHOLD_S = 5.0   # must be absent this long before counting as sold

# COCO classes considered food / drink (the only ones we count)
FOOD_DRINK_CLASSES = {
    "bottle", "wine glass", "cup", "bowl",
    "banana", "apple", "sandwich", "orange",
    "broccoli", "carrot", "hot dog", "pizza",
    "donut", "cake",
}

# Fair NYC retail prices (USD)
PRICES = {
    "bottle":     2.50,   # bottled water/soda
    "wine glass": 8.00,   # glass of wine
    "cup":        4.00,   # coffee/tea cup
    "bowl":       9.00,   # poke / grain bowl
    "banana":     0.75,
    "apple":      1.50,
    "sandwich":   9.50,
    "orange":     1.50,
    "broccoli":   2.50,
    "carrot":     1.00,
    "hot dog":    4.00,
    "pizza":      3.50,   # per slice
    "donut":      2.00,
    "cake":       5.00,   # per slice
}

# Freshness windows (hours). Items not in this dict have no expiry.
FRESHNESS_HOURS = {
    "sandwich": 4, "hot dog": 4, "donut": 4, "cake": 4,
    "pizza": 4,    "bowl":    4,
    "apple": 24, "banana": 24, "orange": 24,
    "broccoli": 24, "carrot": 24,
    # bottle / cup / wine glass: no expiry
}

CSV_HEADER = ["time", "camera_id", "product", "quantity", "price_usd", "on_display_seconds"]


def is_food_drink(label: str) -> bool:
    return label in FOOD_DRINK_CLASSES


class SalesTracker:
    def __init__(self, csv_dir: str, camera_id: int = 0):
        """
        camera_id distinguishes which physical camera generated a sale —
        one process can run multiple trackers (one per slot). Every CSV row
        is tagged with this id so cross-camera reads can filter or aggregate.
        Camera 0 is the legacy/primary slot for backwards compatibility.
        """
        self.csv_dir    = csv_dir
        self.camera_id  = camera_id
        os.makedirs(csv_dir, exist_ok=True)
        self.lock          = threading.Lock()
        self.tracks        = {}     # track_id -> dict
        self.recent_sales  = []     # rolling list of last 50 sales (newest last)
        self.daily_totals  = {"date": None, "count": 0, "revenue_usd": 0.0}
        # Restore today's totals from the on-disk CSV so a server restart
        # mid-day doesn't reset the dashboard counters back to zero.
        self._restore_today_from_csv()

    def _restore_today_from_csv(self):
        """
        Re-hydrate this tracker's daily totals from the shared CSV, filtered
        to this camera_id. Rows missing the column are treated as camera 0
        for backwards compatibility with pre-multi-cam CSVs.
        """
        today = datetime.now().strftime("%Y-%m-%d")
        path  = os.path.join(self.csv_dir, f"veratori-sales-{today}.csv")
        if not os.path.exists(path):
            return
        count = 0
        revenue = 0.0
        try:
            with open(path, "r", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        cam = int(row.get("camera_id", 0) or 0)
                    except (TypeError, ValueError):
                        cam = 0
                    if cam != self.camera_id:
                        continue
                    try:
                        revenue += float(row.get("price_usd", 0) or 0)
                        count   += int(row.get("quantity", 1) or 1)
                    except (TypeError, ValueError):
                        continue
        except Exception as e:
            print(f"[sales] could not restore today's totals: {e}")
            return
        self.daily_totals = {"date": today, "count": count, "revenue_usd": revenue}
        if count:
            print(f"[sales cam{self.camera_id}] restored from CSV: {count} sales, ${revenue:.2f}")

    def _ensure_today(self):
        """Roll daily_totals over to a new day if the calendar date has changed."""
        today = datetime.now().strftime("%Y-%m-%d")
        if self.daily_totals["date"] != today:
            self.daily_totals = {"date": today, "count": 0, "revenue_usd": 0.0}

    # ── Frame update ───────────────────────────────────────────────────────────
    def update(self, detections):
        """
        detections: list of {"track_id": int, "label": str, "conf": float}
        Returns: list of newly emitted sales (each a dict).
        """
        now = time.time()
        seen_ids = set()
        new_sales = []

        with self.lock:
            for det in detections:
                tid   = det.get("track_id")
                label = det.get("label", "")
                if tid is None or not is_food_drink(label):
                    continue
                seen_ids.add(tid)

                track = self.tracks.get(tid)
                if track is None:
                    self.tracks[tid] = {
                        "label":               label,
                        "first_seen":          now,
                        "last_seen":           now,
                        "state":               "NEW",
                        "entered_display_at":  None,
                    }
                else:
                    track["last_seen"] = now
                    if track["state"] == "NEW" and (now - track["first_seen"]) >= APPEARANCE_THRESHOLD_S:
                        track["state"]              = "IN_DISPLAY"
                        track["entered_display_at"] = track["first_seen"]

            # Items not seen in this frame — check if they've been gone long enough
            to_remove = []
            for tid, track in self.tracks.items():
                if tid in seen_ids:
                    continue
                if (now - track["last_seen"]) >= DISAPPEARANCE_THRESHOLD_S:
                    if track["state"] == "IN_DISPLAY":
                        new_sales.append(self._record_sale(track, now))
                    # NEW items that disappeared before reaching IN_DISPLAY are dropped silently
                    to_remove.append(tid)
            for tid in to_remove:
                del self.tracks[tid]

        return new_sales

    # ── Sale recording ─────────────────────────────────────────────────────────
    def _record_sale(self, track, now):
        label = track["label"]
        price = PRICES.get(label, 0.0)
        on_display = int(now - (track["entered_display_at"] or track["first_seen"]))

        local = datetime.fromtimestamp(now)
        sale = {
            "label":               label,
            "price_usd":           price,
            "time":                now,
            "time_iso":            local.isoformat(timespec="seconds"),
            "time_display":        local.strftime("%H:%M:%S"),
            "on_display_seconds":  on_display,
        }

        # Rotate daily totals at midnight
        self._ensure_today()
        self.daily_totals["count"]       += 1
        self.daily_totals["revenue_usd"] += price

        self._append_csv(sale, self.daily_totals["date"])

        self.recent_sales.append(sale)
        if len(self.recent_sales) > 50:
            self.recent_sales = self.recent_sales[-50:]

        print(f"[sales] SOLD: {label} @ ${price:.2f} (on display {on_display}s)")
        return sale

    def _append_csv(self, sale, date_str):
        path = os.path.join(self.csv_dir, f"veratori-sales-{date_str}.csv")
        is_new = not os.path.exists(path)
        try:
            with open(path, "a", newline="") as f:
                w = csv.writer(f)
                if is_new:
                    w.writerow(CSV_HEADER)
                w.writerow([
                    sale["time_iso"],
                    self.camera_id,
                    sale["label"],
                    1,
                    f"{sale['price_usd']:.2f}",
                    sale["on_display_seconds"],
                ])
                f.flush()
        except Exception as e:
            print(f"[sales] CSV write failed: {e}")

    # ── Read APIs ──────────────────────────────────────────────────────────────
    def get_inventory(self):
        """Items currently IN_DISPLAY, grouped by label, with freshness flag."""
        now = time.time()
        grouped = {}
        with self.lock:
            for track in self.tracks.values():
                if track["state"] != "IN_DISPLAY":
                    continue
                label = track["label"]
                age   = int(now - (track["entered_display_at"] or track["first_seen"]))
                row = grouped.setdefault(label, {
                    "label":                  label,
                    "count":                  0,
                    "oldest_display_seconds": 0,
                    "expiring":               False,
                    "price_usd":              PRICES.get(label, 0.0),
                })
                row["count"] += 1
                if age > row["oldest_display_seconds"]:
                    row["oldest_display_seconds"] = age
                fresh_h = FRESHNESS_HOURS.get(label)
                if fresh_h and age >= fresh_h * 3600:
                    row["expiring"] = True
        return sorted(grouped.values(), key=lambda r: -r["count"])

    def get_sales_summary(self):
        with self.lock:
            self._ensure_today()
            recent = list(self.recent_sales[-20:])
            recent.reverse()  # newest first for the UI
            today = dict(self.daily_totals)
        return {"today": today, "recent": recent}

    # ── Alerts (derived from perishable inventory) ─────────────────────────────
    def get_alerts(self):
        """
        Derive System Alerts from items currently IN_DISPLAY whose freshness
        window is being approached or exceeded. Non-perishable items
        (bottle / cup / wine glass) are never alerted on.

        Returns: list of {alert_type, product_name, message, timestamp_est}
        """
        now = time.time()
        alerts = []

        # Group tracks by label and find the worst-case (oldest) item per label
        worst_by_label = {}
        with self.lock:
            for track in self.tracks.values():
                if track["state"] != "IN_DISPLAY":
                    continue
                label = track["label"]
                if label not in FRESHNESS_HOURS:
                    continue
                age = now - (track["entered_display_at"] or track["first_seen"])
                cur = worst_by_label.get(label)
                if cur is None or age > cur["age"]:
                    worst_by_label[label] = {"age": age, "entered_at": track["entered_display_at"]}

        for label, info in worst_by_label.items():
            fresh_h    = FRESHNESS_HOURS[label]
            window_s   = fresh_h * 3600
            age_s      = info["age"]
            pct        = age_s / window_s if window_s > 0 else 0
            entered_at = datetime.fromtimestamp(info["entered_at"])
            age_str    = _fmt_duration(int(age_s))

            if pct >= 1.0:
                alerts.append({
                    "alert_type":    "critical",
                    "product_name":  label.title(),
                    "message":       f"{label.title()} has been on display for {age_str} — past the {fresh_h}h freshness window. Remove from display immediately.",
                    "timestamp_est": entered_at.strftime("%H:%M EST"),
                })
            elif pct >= 0.75:
                remaining_s = max(window_s - age_s, 0)
                alerts.append({
                    "alert_type":    "expiration",
                    "product_name":  label.title(),
                    "message":       f"{label.title()} on display for {age_str} — approaching {fresh_h}h freshness limit ({_fmt_duration(int(remaining_s))} remaining). Plan to rotate or pull soon.",
                    "timestamp_est": entered_at.strftime("%H:%M EST"),
                })
            # Below 75% → no alert (don't spam)

        # Sort by alert_type priority (critical first)
        order = {"critical": 0, "expiration": 1, "warning": 2, "info": 3}
        alerts.sort(key=lambda a: order.get(a["alert_type"], 99))
        return alerts


    # ── Report aggregation (multi-day CSV scan) ────────────────────────────────
    def get_report(self, start_date: str, end_date: str, camera_id: int = None):
        """
        camera_id=None → aggregate ALL cameras for the report window (default).
        camera_id=N    → only rows tagged with that camera (or untagged legacy
                         rows when N == 0).
        """
        """
        Aggregate sales across all CSVs falling in [start_date, end_date] (YYYY-MM-DD inclusive).

        Returns a dict shaped for the PDF template:
          {
            "period":         {"start","end","days"},
            "kpis":           {"revenue","units","top_product","avg_on_display_s","best_day"},
            "daily":          [{"date","units","revenue"}, ...]   (one per day, gaps zero-filled)
            "hourly":         [{"hour","units","revenue"}, ...]   (24 buckets)
            "top_products":   [{"label","units","revenue","share"}, ...]  (sorted desc)
            "transactions":   [{"time","product","price"}, ...]   (last 20 newest first)
            "totals":         {"files_read","rows_read"}
          }
        """
        try:
            d0 = datetime.strptime(start_date, "%Y-%m-%d").date()
            d1 = datetime.strptime(end_date,   "%Y-%m-%d").date()
        except ValueError:
            return None
        if d1 < d0:
            d0, d1 = d1, d0

        # Pre-seed daily buckets so gaps render as zeros
        days = (d1 - d0).days + 1
        daily = {}
        cur = d0
        while cur <= d1:
            daily[cur.isoformat()] = {"date": cur.isoformat(), "units": 0, "revenue": 0.0}
            cur += timedelta(days=1)

        hourly  = [{"hour": h, "units": 0, "revenue": 0.0} for h in range(24)]
        products = {}            # label -> {units, revenue, on_display_s_sum, on_display_n}
        all_rows = []            # for transactions tail
        files_read = 0
        rows_read  = 0

        cur = d0
        while cur <= d1:
            path = os.path.join(self.csv_dir, f"veratori-sales-{cur.isoformat()}.csv")
            if os.path.exists(path):
                files_read += 1
                try:
                    with open(path, "r", newline="") as f:
                        for row in csv.DictReader(f):
                            try:
                                price = float(row.get("price_usd") or 0)
                                qty   = int(row.get("quantity")    or 1)
                                label = (row.get("product") or "").strip() or "unknown"
                                t_iso = row.get("time") or ""
                                on_s  = int(row.get("on_display_seconds") or 0)
                                cam   = int(row.get("camera_id", 0) or 0)
                            except (TypeError, ValueError):
                                continue
                            if camera_id is not None and cam != camera_id:
                                continue

                            rows_read += 1
                            d_iso = cur.isoformat()
                            daily[d_iso]["units"]   += qty
                            daily[d_iso]["revenue"] += price

                            # Hour bucket (from ISO timestamp)
                            try:
                                hr = datetime.fromisoformat(t_iso).hour
                            except Exception:
                                hr = 0
                            hourly[hr]["units"]   += qty
                            hourly[hr]["revenue"] += price

                            p = products.setdefault(label, {
                                "label": label, "units": 0, "revenue": 0.0,
                                "on_display_s_sum": 0, "on_display_n": 0,
                            })
                            p["units"]            += qty
                            p["revenue"]          += price
                            p["on_display_s_sum"] += on_s
                            p["on_display_n"]     += 1

                            all_rows.append({"time": t_iso, "product": label, "price": price})
                except Exception as e:
                    print(f"[report] read failed for {path}: {e}")
            cur += timedelta(days=1)

        # KPI rollups
        total_units   = sum(d["units"]   for d in daily.values())
        total_revenue = sum(d["revenue"] for d in daily.values())
        on_disp_sum   = sum(p["on_display_s_sum"] for p in products.values())
        on_disp_n     = sum(p["on_display_n"]    for p in products.values())
        avg_on_disp_s = int(on_disp_sum / on_disp_n) if on_disp_n else 0

        top_list = sorted(products.values(), key=lambda r: -r["revenue"])
        top_product = top_list[0]["label"].title() if top_list else "—"
        for p in top_list:
            p["share"] = round(p["revenue"] / total_revenue * 100, 1) if total_revenue else 0.0
            p.pop("on_display_s_sum", None)
            p.pop("on_display_n",     None)

        best_day = max(daily.values(), key=lambda d: d["revenue"]) if daily else None

        all_rows.sort(key=lambda r: r["time"], reverse=True)
        tail = all_rows[:20]

        return {
            "period": {"start": d0.isoformat(), "end": d1.isoformat(), "days": days},
            "kpis": {
                "revenue":          round(total_revenue, 2),
                "units":            total_units,
                "top_product":      top_product,
                "avg_on_display_s": avg_on_disp_s,
                "best_day":         best_day,
            },
            "daily":        list(daily.values()),
            "hourly":       hourly,
            "top_products": top_list[:10],
            "transactions": tail,
            "totals":       {"files_read": files_read, "rows_read": rows_read},
        }


def _fmt_duration(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m {seconds % 60}s"
    h = seconds // 3600
    m = (seconds % 3600) // 60
    return f"{h}h {m}m"
