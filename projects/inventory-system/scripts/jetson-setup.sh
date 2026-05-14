#!/usr/bin/env bash
#
# Veratori Jetson franchise deployment script.
#
# Run once on a fresh Jetson (Orin Nano / NX) to:
#   1. Install Python deps + ffmpeg
#   2. Install Cloudflare tunnel client (cloudflared)
#   3. Create a named tunnel for this franchise
#   4. Route DNS so https://<franchise>.cam.veratori.com → this Jetson
#   5. Install camera_server and cloudflared as systemd services so they
#      survive reboots and crash-restart automatically.
#
# Usage:
#   bash jetson-setup.sh <franchise_id> [domain]
#
# Example:
#   bash jetson-setup.sh canal
#   bash jetson-setup.sh f45  cam.veratori.com
#
# Prerequisites:
#   * Repository is already cloned to /opt/veratori/inventory-system
#   * Domain is added to your Cloudflare account
#   * Python 3.10+ installed (default on JetPack 6)

set -euo pipefail

FRANCHISE_ID="${1:?Usage: $0 <franchise_id>}"
DOMAIN="${2:-cam.veratori.com}"
TUNNEL_NAME="veratori-${FRANCHISE_ID}"
TUNNEL_HOST="${FRANCHISE_ID}.${DOMAIN}"
INSTALL_DIR="${INSTALL_DIR:-/opt/veratori/inventory-system}"
SERVICE_USER="${SUDO_USER:-$USER}"

echo "=== Veratori Jetson setup ==="
echo "Franchise:   $FRANCHISE_ID"
echo "Tunnel host: $TUNNEL_HOST"
echo "Install dir: $INSTALL_DIR"
echo

# ── 1. System packages ────────────────────────────────────────────
echo "[1/6] Installing system packages…"
sudo apt-get update -qq
sudo apt-get install -y -qq python3-pip python3-venv ffmpeg curl

# ── 2. Python venv + deps ─────────────────────────────────────────
echo "[2/6] Setting up Python venv at $INSTALL_DIR/.venv …"
cd "$INSTALL_DIR"
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
./.venv/bin/pip install --quiet --upgrade pip
./.venv/bin/pip install --quiet ultralytics opencv-python python-docx matplotlib lap firebase-admin

# Optional: TensorRT engine build for ~4-6x faster inference on Jetson
if [[ -f models/yolov8n.pt && ! -f models/yolov8n.engine ]]; then
  echo "[2b] Building TensorRT FP16 engine (one-time, ~30s)…"
  ./.venv/bin/yolo export model=models/yolov8n.pt format=engine half=True device=0 imgsz=416 || \
    echo "  [warn] TensorRT export failed — falling back to PyTorch weights"
fi

# ── 3. Cloudflared install ────────────────────────────────────────
echo "[3/6] Installing cloudflared…"
ARCH="$(dpkg --print-architecture)"
case "$ARCH" in
  arm64|aarch64) PKG=cloudflared-linux-arm64.deb ;;
  amd64|x86_64)  PKG=cloudflared-linux-amd64.deb ;;
  *) echo "Unsupported architecture: $ARCH"; exit 1 ;;
esac
curl -L --silent --output /tmp/cloudflared.deb \
  "https://github.com/cloudflare/cloudflared/releases/latest/download/${PKG}"
sudo dpkg -i /tmp/cloudflared.deb >/dev/null

# ── 4. Tunnel auth + creation ─────────────────────────────────────
echo "[4/6] Authenticating with Cloudflare (opens a browser link to confirm)…"
if [[ ! -f "$HOME/.cloudflared/cert.pem" ]]; then
  cloudflared tunnel login
fi

if ! cloudflared tunnel list 2>/dev/null | grep -q "$TUNNEL_NAME"; then
  echo "[4a] Creating tunnel '$TUNNEL_NAME'…"
  cloudflared tunnel create "$TUNNEL_NAME"
fi

TUNNEL_ID="$(cloudflared tunnel list | awk -v n="$TUNNEL_NAME" '$2==n {print $1}')"
if [[ -z "$TUNNEL_ID" ]]; then
  echo "ERROR: could not resolve tunnel id for $TUNNEL_NAME" >&2
  exit 2
fi

# ── 5. Tunnel config + DNS route ──────────────────────────────────
echo "[5/6] Writing tunnel config + routing $TUNNEL_HOST → this Jetson…"
mkdir -p "$HOME/.cloudflared"
cat > "$HOME/.cloudflared/config.yml" <<EOF
tunnel: $TUNNEL_ID
credentials-file: $HOME/.cloudflared/$TUNNEL_ID.json

# Only the camera_server port is exposed. Anything else returns 404.
ingress:
  - hostname: $TUNNEL_HOST
    service: http://localhost:5001
  - service: http_status:404
EOF

cloudflared tunnel route dns "$TUNNEL_NAME" "$TUNNEL_HOST" || \
  echo "  [info] DNS route may already exist — continuing"

# ── 6. Franchise + Firebase auth env files ────────────────────────
echo "[6/7] Provisioning per-franchise auth env…"
sudo mkdir -p /etc/veratori
sudo chmod 0755 /etc/veratori

# franchise.env tells sync_agent.py which franchise this Jetson is.
sudo tee /etc/veratori/franchise.env >/dev/null <<EOF
FRANCHISE_ID=$FRANCHISE_ID
EOF
sudo chmod 0644 /etc/veratori/franchise.env

# jetson-auth.env holds this Jetson's Firebase Auth identity (created by the
# owner via the provisionJetson Cloud Function on the dashboard). The values
# scope this Jetson's writes — Firestore rules reject writes for any other
# franchise_id. If a Jetson is compromised, blast radius = its own franchise.
#
# Expected fields:
#   FIREBASE_EMAIL=jetson-<franchise>@bot.veratori.local
#   FIREBASE_PASSWORD=<24-char random, returned by provisionJetson>
#   FIREBASE_API_KEY=AIzaSyBTBYkalSjJBQjOZYetfySmG9ByEgWCcJo
#   FIREBASE_PROJECT_ID=veratori-f3a5a
if [[ ! -f /etc/veratori/jetson-auth.env ]]; then
  if [[ -f "$INSTALL_DIR/jetson-auth.env" ]]; then
    sudo cp "$INSTALL_DIR/jetson-auth.env" /etc/veratori/jetson-auth.env
    sudo chmod 0600 /etc/veratori/jetson-auth.env
    echo "  [info] installed jetson-auth.env from repo root"
  else
    echo "  [warn] /etc/veratori/jetson-auth.env missing — sync_agent will not start."
    echo "         From an owner browser session, open the Veratori dashboard →"
    echo "         Account → Team → Provision Jetson → select '$FRANCHISE_ID'."
    echo "         Copy the returned credentials into /etc/veratori/jetson-auth.env"
    echo "         (mode 0600, root-owned) then run:"
    echo "         sudo systemctl enable --now veratori-sync.service"
  fi
fi

# ── 7. Systemd services ───────────────────────────────────────────
echo "[7/7] Installing systemd services…"

# Camera server
sudo tee /etc/systemd/system/veratori-camera.service >/dev/null <<EOF
[Unit]
Description=Veratori Camera Server (YOLO + sales tracker)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
Environment=PYTHONUNBUFFERED=1
ExecStart=$INSTALL_DIR/.venv/bin/python $INSTALL_DIR/camera_server.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Sync agent (sales + alerts → Firestore via per-franchise Firebase identity)
sudo tee /etc/systemd/system/veratori-sync.service >/dev/null <<EOF
[Unit]
Description=Veratori Sync Agent (Firestore sales + alerts push)
After=network-online.target veratori-camera.service
Wants=network-online.target

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
EnvironmentFile=/etc/veratori/franchise.env
EnvironmentFile=/etc/veratori/jetson-auth.env
Environment=PYTHONUNBUFFERED=1
ExecStart=$INSTALL_DIR/.venv/bin/python $INSTALL_DIR/sync_agent.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Cloudflared tunnel (managed natively by cloudflared service install)
sudo cloudflared --config "$HOME/.cloudflared/config.yml" service install || \
  echo "  [info] cloudflared service already installed"

sudo systemctl daemon-reload
sudo systemctl enable --now veratori-camera.service
sudo systemctl enable --now cloudflared.service
if [[ -f /etc/veratori/jetson-auth.env ]]; then
  sudo systemctl enable --now veratori-sync.service
fi

# Wait briefly + emit health check
sleep 5
echo
echo "=== Done ==="
echo "Camera server:    $(systemctl is-active veratori-camera) (port 5001 local)"
echo "Sync agent:       $(systemctl is-active veratori-sync 2>/dev/null || echo not-installed)"
echo "Cloudflare tunnel: $(systemctl is-active cloudflared)"
echo
echo "Verify from any device on the internet:"
echo "  curl https://$TUNNEL_HOST/status"
echo
echo "If status returns JSON with connected:true → tunnel is live."
echo "View live dashboard at:  https://veratori-f3a5a.web.app/index.html?loc=$FRANCHISE_ID"
