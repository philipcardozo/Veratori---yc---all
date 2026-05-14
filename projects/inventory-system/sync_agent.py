#!/usr/bin/env python3
"""
Veratori sync agent — pushes sales + alerts from a Jetson franchise to Firestore.

Runs alongside camera_server.py as a sibling systemd unit (veratori-sync.service).

PHASE C IDENTITY MODEL
----------------------
This agent does NOT use the Firebase admin SDK. Each Jetson holds a per-franchise
Firebase Auth identity (`jetson-<franchise>@bot.veratori.local`) with custom
claims `{role: 'jetson', franchise: '<franchise>'}`. Writes go through the
Firestore REST API as that user, scoped by Firestore rules so a compromised
Jetson can only affect its own franchise's data.

Per-franchise credentials are provisioned by the `provisionJetson` Cloud
Function (owner-only) and copied to `/etc/veratori/jetson-auth.env`.

Inputs
------
  /etc/veratori/franchise.env       FRANCHISE_ID=<id>
  /etc/veratori/jetson-auth.env     FIREBASE_EMAIL=<>, FIREBASE_PASSWORD=<>,
                                    FIREBASE_API_KEY=<>, FIREBASE_PROJECT_ID=<>
  ./sales/veratori-sales-YYYY-MM-DD.csv     (tailed by byte offset)
  http://127.0.0.1:5001/alerts              (polled from camera_server)

Outputs (Firestore — top-level collections per project_veratori_firestore_schema)
  sales/{franchise}-cam{cam}-{epoch_ms}-{product}
  alerts/{sha1(franchise|type|product|slot|hh:mm)}

State
  ./.sync_state.json   { last_csv_date, last_byte_offset, alert_hashes }

Failure model
  Token expired (401): refresh once; on second 401, sign in again from scratch.
  Network down: byte offset not advanced; next tick retries.
  Camera server down: /alerts poll silently fails; sales tick keeps going.
"""

import csv
import hashlib
import json
import os
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen, Request

ROOT        = Path(__file__).resolve().parent
SALES_DIR   = ROOT / "sales"
STATE_FILE  = ROOT / ".sync_state.json"
ALERTS_URL  = os.environ.get("VERATORI_LOCAL_URL", "http://127.0.0.1:5001") + "/alerts"
SALES_TICK  = int(os.environ.get("VERATORI_SALES_TICK", "60"))
ALERTS_TICK = int(os.environ.get("VERATORI_ALERTS_TICK", "5"))
BATCH_LIMIT = 500
TOKEN_EARLY_REFRESH_SEC = 300   # refresh 5 min before expiry


# ── Config ────────────────────────────────────────────────────────────────────
def _load_env_file(path: Path) -> dict:
    """Parse a simple KEY=value env file. Strips quotes, ignores comments."""
    out = {}
    if not path.exists():
        return out
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        out[key.strip()] = val.strip().strip('"').strip("'")
    return out


def _load_config() -> dict:
    """Compose config from /etc/veratori/*.env, with env-var fallbacks."""
    franchise_env = _load_env_file(Path("/etc/veratori/franchise.env"))
    auth_env      = _load_env_file(Path("/etc/veratori/jetson-auth.env"))

    franchise_id = (franchise_env.get("FRANCHISE_ID")
                    or os.environ.get("FRANCHISE_ID"))
    email        = (auth_env.get("FIREBASE_EMAIL")
                    or os.environ.get("FIREBASE_EMAIL"))
    password     = (auth_env.get("FIREBASE_PASSWORD")
                    or os.environ.get("FIREBASE_PASSWORD"))
    api_key      = (auth_env.get("FIREBASE_API_KEY")
                    or os.environ.get("FIREBASE_API_KEY"))
    project_id   = (auth_env.get("FIREBASE_PROJECT_ID")
                    or os.environ.get("FIREBASE_PROJECT_ID")
                    or "veratori-f3a5a")

    missing = [k for k, v in
               (("FRANCHISE_ID", franchise_id),
                ("FIREBASE_EMAIL", email),
                ("FIREBASE_PASSWORD", password),
                ("FIREBASE_API_KEY", api_key))
               if not v]
    if missing:
        sys.exit(
            f"[sync] missing config: {', '.join(missing)}.\n"
            "Provision per-franchise credentials by calling the provisionJetson "
            "Cloud Function (owner-only), then copy the output to "
            "/etc/veratori/jetson-auth.env."
        )

    return {
        "franchise_id": franchise_id,
        "email":        email,
        "password":     password,
        "api_key":      api_key,
        "project_id":   project_id,
    }


# ── Firebase REST client (auth + Firestore writes) ────────────────────────────
class FirebaseRestClient:
    """Minimal Firebase Identity Toolkit + Firestore REST client.

    Holds an idToken + refreshToken. Refreshes the idToken proactively before
    expiry, and reactively on 401. Exposes batch_commit() for Firestore writes
    via the documents:commit endpoint.
    """

    def __init__(self, email: str, password: str, api_key: str, project_id: str):
        self.email      = email
        self.password   = password
        self.api_key    = api_key
        self.project_id = project_id
        self.id_token       = None
        self.refresh_token  = None
        self.token_expires  = 0.0

    # ── Auth ──────────────────────────────────────────────────────────────────
    def _http_post(self, url: str, body, headers=None, timeout=10):
        if isinstance(body, (dict, list)):
            data = json.dumps(body).encode("utf-8")
            hdrs = {"Content-Type": "application/json"}
        else:
            data = body.encode("utf-8")
            hdrs = {"Content-Type": "application/x-www-form-urlencoded"}
        if headers:
            hdrs.update(headers)
        req = Request(url, data=data, headers=hdrs, method="POST")
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def sign_in(self) -> None:
        """Initial sign-in with email+password. Populates id/refresh token."""
        url = (
            "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"
            f"?key={self.api_key}"
        )
        body = {"email": self.email, "password": self.password,
                "returnSecureToken": True}
        try:
            resp = self._http_post(url, body)
        except HTTPError as e:
            err = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"sign-in failed ({e.code}): {err}") from e

        self.id_token      = resp["idToken"]
        self.refresh_token = resp["refreshToken"]
        self.token_expires = time.time() + int(resp.get("expiresIn", 3600))
        print(f"[sync] signed in as {self.email} (token valid {resp.get('expiresIn')}s)",
              flush=True)

    def refresh(self) -> None:
        """Exchange the refresh token for a new idToken."""
        if not self.refresh_token:
            return self.sign_in()
        url  = f"https://securetoken.googleapis.com/v1/token?key={self.api_key}"
        body = f"grant_type=refresh_token&refresh_token={self.refresh_token}"
        try:
            resp = self._http_post(url, body)
        except HTTPError as e:
            # If refresh fails (token revoked, etc.), do a full sign-in.
            print(f"[sync] refresh failed ({e.code}) — re-signing in", flush=True)
            return self.sign_in()
        self.id_token      = resp["id_token"]
        self.refresh_token = resp.get("refresh_token", self.refresh_token)
        self.token_expires = time.time() + int(resp.get("expires_in", 3600))
        print("[sync] refreshed id token", flush=True)

    def ensure_token(self) -> str:
        if not self.id_token:
            self.sign_in()
        elif time.time() > self.token_expires - TOKEN_EARLY_REFRESH_SEC:
            self.refresh()
        return self.id_token

    # ── Firestore writes ──────────────────────────────────────────────────────
    @staticmethod
    def _to_value(v):
        """Convert a Python value to a Firestore REST `Value` JSON object."""
        if v is None:
            return {"nullValue": None}
        if isinstance(v, bool):
            return {"booleanValue": v}
        if isinstance(v, int):
            return {"integerValue": str(v)}
        if isinstance(v, float):
            return {"doubleValue": v}
        if isinstance(v, str):
            return {"stringValue": v}
        if isinstance(v, datetime):
            iso = v.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
            return {"timestampValue": iso}
        if isinstance(v, list):
            return {"arrayValue": {"values": [FirebaseRestClient._to_value(x) for x in v]}}
        if isinstance(v, dict):
            return {"mapValue": {"fields": {k: FirebaseRestClient._to_value(val)
                                            for k, val in v.items()}}}
        raise TypeError(f"Unsupported Firestore value type: {type(v).__name__}")

    def _doc_path(self, collection: str, doc_id: str) -> str:
        return (f"projects/{self.project_id}/databases/(default)"
                f"/documents/{collection}/{doc_id}")

    def make_set_write(self, collection: str, doc_id: str, fields: dict) -> dict:
        """Build a Firestore Write entry that creates-or-replaces a doc."""
        return {
            "update": {
                "name":   self._doc_path(collection, doc_id),
                "fields": {k: self._to_value(v) for k, v in fields.items()},
            },
        }

    def make_patch_write(self, collection: str, doc_id: str, fields: dict) -> dict:
        """Build a Firestore Write entry that patches only `fields`."""
        return {
            "update": {
                "name":   self._doc_path(collection, doc_id),
                "fields": {k: self._to_value(v) for k, v in fields.items()},
            },
            "updateMask": {"fieldPaths": list(fields.keys())},
        }

    def batch_commit(self, writes: list) -> None:
        """POST a list of Write entries to Firestore documents:commit.

        On 401, refresh once and retry. Any other failure raises.
        """
        if not writes:
            return
        url = (f"https://firestore.googleapis.com/v1/projects/"
               f"{self.project_id}/databases/(default)/documents:commit")
        body = {"writes": writes}

        def _attempt():
            token = self.ensure_token()
            req = Request(
                url,
                data=json.dumps(body).encode("utf-8"),
                headers={
                    "Content-Type":  "application/json",
                    "Authorization": f"Bearer {token}",
                },
                method="POST",
            )
            with urlopen(req, timeout=15) as resp:
                resp.read()  # drain
            return True

        try:
            _attempt()
        except HTTPError as e:
            if e.code == 401:
                self.refresh()
                _attempt()
            else:
                err = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else ""
                raise RuntimeError(f"firestore commit failed ({e.code}): {err}") from e


# ── State persistence ─────────────────────────────────────────────────────────
def _load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {"last_csv_date": None, "last_byte_offset": 0, "alert_hashes": {}}


def _save_state(state: dict) -> None:
    tmp = STATE_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state))
    tmp.replace(STATE_FILE)


# ── Doc id helpers ────────────────────────────────────────────────────────────
def _today_csv_path() -> Path:
    return SALES_DIR / f"veratori-sales-{datetime.now().strftime('%Y-%m-%d')}.csv"


def _safe(s: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in (s or "")).strip("_") or "x"


def _sale_doc_id(franchise_id: str, camera_id: int, ts_iso: str, product: str) -> str:
    try:
        epoch_ms = int(datetime.fromisoformat(ts_iso).timestamp() * 1000)
    except ValueError:
        epoch_ms = int(time.time() * 1000)
    return f"{franchise_id}-cam{camera_id}-{epoch_ms}-{_safe(product)}"


def _alert_doc_id(franchise_id: str, alert: dict) -> str:
    raw = "|".join(str(alert.get(k, "")) for k in (
        "alert_type", "product_name", "slot", "timestamp_est"))
    return hashlib.sha1(f"{franchise_id}|{raw}".encode()).hexdigest()


# ── Sales tick ────────────────────────────────────────────────────────────────
def tick_sales(client: FirebaseRestClient, franchise_id: str, state: dict) -> None:
    today = datetime.now().strftime("%Y-%m-%d")
    if state.get("last_csv_date") != today:
        state["last_csv_date"]    = today
        state["last_byte_offset"] = 0

    csv_path = _today_csv_path()
    if not csv_path.exists():
        return

    size   = csv_path.stat().st_size
    offset = state["last_byte_offset"]
    if offset > size:
        offset = 0  # file rotated/truncated — re-scan

    with csv_path.open("r", newline="") as f:
        if offset == 0:
            reader = csv.DictReader(f)
            rows = list(reader)
        else:
            f.seek(0)
            header = next(csv.reader(f))
            f.seek(offset)
            reader = csv.DictReader(f, fieldnames=header)
            rows = list(reader)
        new_offset = f.tell()

    if not rows:
        if new_offset != state["last_byte_offset"]:
            state["last_byte_offset"] = new_offset
            _save_state(state)
        return

    pending = []
    pushed  = 0
    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    for row in rows:
        try:
            ts_iso     = row["time"]
            camera_id  = int(row.get("camera_id") or 0)
            product    = (row.get("product") or "").strip().lower()
            quantity   = int(row.get("quantity") or 1)
            price      = float(row.get("price_usd") or 0.0)
            on_display = int(row.get("on_display_seconds") or 0)
        except (KeyError, TypeError, ValueError) as e:
            print(f"[sync] skip malformed row {row}: {e}", flush=True)
            continue

        try:
            epoch_ms = int(datetime.fromisoformat(ts_iso).timestamp() * 1000)
        except ValueError:
            epoch_ms = int(time.time() * 1000)

        doc_id = _sale_doc_id(franchise_id, camera_id, ts_iso, product)
        pending.append(client.make_set_write("sales", doc_id, {
            "franchise_id":       franchise_id,
            "camera_id":          camera_id,
            "ts":                 ts_iso,
            "ts_epoch_ms":        epoch_ms,
            "product":            product,
            "quantity":           quantity,
            "price_usd":          price,
            "on_display_seconds": on_display,
            "ingested_at":        now_iso,
        }))
        pushed += 1

        if len(pending) >= BATCH_LIMIT:
            client.batch_commit(pending)
            pending = []

    if pending:
        client.batch_commit(pending)

    state["last_byte_offset"] = new_offset
    _save_state(state)
    print(f"[sync] sales: pushed {pushed} rows (offset={new_offset})", flush=True)


# ── Alerts tick ───────────────────────────────────────────────────────────────
def tick_alerts(client: FirebaseRestClient, franchise_id: str, state: dict) -> None:
    try:
        with urlopen(ALERTS_URL, timeout=2) as r:
            current = json.loads(r.read().decode())
    except (URLError, TimeoutError, json.JSONDecodeError, ConnectionError):
        return

    if not isinstance(current, list):
        return

    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    seen    = {}
    writes  = []
    new     = 0

    for alert in current:
        h = _alert_doc_id(franchise_id, alert)
        seen[h] = 1
        if h in state.get("alert_hashes", {}):
            continue
        writes.append(client.make_set_write("alerts", h, {
            "franchise_id":  franchise_id,
            "alert_type":    alert.get("alert_type"),
            "product_name":  alert.get("product_name"),
            "message":       alert.get("message"),
            "timestamp_est": alert.get("timestamp_est"),
            "slot":          alert.get("slot", 0),
            "camera_name":   alert.get("camera_name", ""),
            "first_seen":    now_iso,
            "created_at":    now_iso,
            "resolved_at":   None,
        }))
        new += 1

    previous = state.get("alert_hashes", {})
    resolved = [h for h in previous if h not in seen]
    for h in resolved:
        # Patch only resolved_at — keeps existing fields untouched.
        # Note: franchise_id must remain unchanged for the rule to allow the
        # update (it checks both resource.data and request.resource.data).
        writes.append(client.make_patch_write("alerts", h, {
            "resolved_at": now_iso,
        }))

    if writes:
        try:
            client.batch_commit(writes)
        except Exception as e:
            print(f"[sync] alerts commit error: {e}", flush=True)
            return

    if new or resolved:
        state["alert_hashes"] = seen
        _save_state(state)
        print(f"[sync] alerts: +{new} new, -{len(resolved)} resolved "
              f"(active={len(seen)})", flush=True)
    elif state.get("alert_hashes") != seen:
        state["alert_hashes"] = seen
        _save_state(state)


# ── Main loop ─────────────────────────────────────────────────────────────────
def main() -> None:
    cfg = _load_config()
    client = FirebaseRestClient(
        email=cfg["email"], password=cfg["password"],
        api_key=cfg["api_key"], project_id=cfg["project_id"],
    )
    try:
        client.sign_in()
    except Exception as e:
        sys.exit(f"[sync] could not authenticate: {e}")

    state = _load_state()
    print(f"[sync] started franchise={cfg['franchise_id']}  "
          f"sales={SALES_TICK}s  alerts={ALERTS_TICK}s", flush=True)

    stop = {"flag": False}

    def _shutdown(*_):
        stop["flag"] = True

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT,  _shutdown)

    next_sales  = 0.0
    next_alerts = 0.0
    while not stop["flag"]:
        now = time.time()
        if now >= next_alerts:
            try:
                tick_alerts(client, cfg["franchise_id"], state)
            except Exception as e:
                print(f"[sync] alerts error: {e}", flush=True)
            next_alerts = time.time() + ALERTS_TICK
        if now >= next_sales:
            try:
                tick_sales(client, cfg["franchise_id"], state)
            except Exception as e:
                print(f"[sync] sales error: {e}", flush=True)
            next_sales = time.time() + SALES_TICK
        time.sleep(max(0.1, min(next_alerts, next_sales) - time.time()))

    print("[sync] shutting down", flush=True)


if __name__ == "__main__":
    main()
