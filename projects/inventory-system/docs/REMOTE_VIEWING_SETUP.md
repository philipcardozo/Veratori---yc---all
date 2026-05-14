# Remote Viewing — Phase A Setup

This runbook is for the **one-time ops work** Felipe does to enable the owner
to view every franchise's cameras + sales from anywhere on the internet.

The frontend code is already in place (`franchise-config.js`, `role-guard.js`).
What's missing is the cloud plumbing (Cloudflare account, domain, tunnels)
and the per-Jetson deployment.

## What you'll have when this is done

- `https://veratori-f3a5a.web.app/` works from any device, any network
- Clicking "Canal Street" on the hub → live YOLO feed from the Jetson in
  Canal Street's location
- Weekly reports, alerts, sales — all routed to the right franchise
  automatically
- Owner sees all 5 locations; managers see only theirs

---

## Step 1 — Cloudflare account + domain (10 min)

1. Sign up at <https://dash.cloudflare.com/sign-up> (free plan is enough).
2. **Add site** → enter `veratori.com` → choose Free plan.
3. Cloudflare gives you two nameservers. At your domain registrar (where you
   bought `veratori.com`), replace the existing nameservers with Cloudflare's.
   DNS propagation: 5 min to a few hours.
4. While waiting, in Cloudflare → **DNS** → confirm `veratori.com` is "Active".

## Step 2 — Reserve subdomain pattern (1 min)

You don't need to manually add DNS records — the Jetson setup script does that
per franchise. But pick the pattern now:

- `canal.cam.veratori.com` → Canal Street Jetson
- `f43.cam.veratori.com`   → 43rd Street Jetson
- `f44.cam.veratori.com`   → 44th Street Jetson
- `f45.cam.veratori.com`   → 45th Street Jetson
- `f46.cam.veratori.com`   → 46th Street Jetson

These IDs must match `franchise-config.js` (they already do).

## Step 3 — First Jetson deployment (~20 min)

On the Jetson:

```bash
# Clone the repo to the standard location
sudo mkdir -p /opt/veratori
sudo chown -R $USER /opt/veratori
cd /opt/veratori
git clone <your-veratori-repo>.git inventory-system
cd inventory-system

# Run the setup script. Replace `canal` with the franchise id.
bash scripts/jetson-setup.sh canal
```

The script will:
- Install Python deps + cloudflared
- Open a browser link asking you to log in to Cloudflare and authorise this
  Jetson (only happens once per Jetson — credentials persist in `~/.cloudflared`)
- Create a Cloudflare tunnel named `veratori-canal`
- Add a DNS CNAME pointing `canal.cam.veratori.com` → the tunnel
- Install the camera server + cloudflared as systemd services
- Print the health-check URL to verify

Verify from your laptop:

```bash
curl https://canal.cam.veratori.com/status
# → {"connected":true,"error":null,"fps":15.2,"yolo":false}
```

If you get that JSON, the franchise is live.

## Step 4 — Verify in the dashboard

Visit <https://veratori-f3a5a.web.app/home.html> in your browser. Click
"Canal Street." The live YOLO feed should appear in the YOLO Live Inventory
panel, just like the local demo — but the actual inference is happening on the
Jetson in Brooklyn (or wherever it physically is).

## Step 5 — Multi-tenant auth (Phase B, after first franchise is live)

Right now every Firebase user sees every franchise. To lock managers to their
own location, set their custom claims via the Firebase Admin SDK.

In `functions/` (or run as a one-off Node script):

```js
const admin = require('firebase-admin');
admin.initializeApp();

// Manager who only sees Canal Street
await admin.auth().setCustomUserClaims('<uid>', {
  role: 'manager',
  franchises: ['canal'],
});

// Owner (you) — sees everything
await admin.auth().setCustomUserClaims('<owner-uid>', {
  role: 'owner',
});
```

The user has to sign out and back in once for the new claims to take effect.

`role-guard.js` in the frontend reads these claims on every page load and
filters the sidebar accordingly. Deep-linking to `?loc=canal` from a manager
without canal access redirects them back to the hub.

---

## Day-2 operations

### Check a franchise's health
```bash
curl https://<franchise>.cam.veratori.com/status
```

### View tunnel logs on the Jetson
```bash
sudo journalctl -u cloudflared -f
sudo journalctl -u veratori-camera -f
```

### Restart a franchise's server
```bash
sudo systemctl restart veratori-camera
```

### Decommission a franchise
On the Jetson:
```bash
sudo systemctl disable --now veratori-camera cloudflared
cloudflared tunnel delete veratori-<franchise>
```

In `franchise-config.js`, remove the entry (and redeploy the frontend).

---

## What's NOT in Phase A

These ship later:

- **Phase B** — Sales/alerts sync to Firestore (so the hub shows network-wide
  KPIs without polling every Jetson)
- **Phase C** — Cloudflare Access policies in front of each tunnel (defence in
  depth on top of the role-guard frontend check)
- **Phase D** — Same setup script enhanced for unattended re-installs
- **Phase E** — Video archive (local NVMe + cloud highlights via R2)
- **Phase F** — ML training data collection pipeline
