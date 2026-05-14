# Cloudflare Access Setup — Veratori

This runbook gates each franchise's tunnel URL (`*.cam.veratori.com`) behind a
Cloudflare Access login. Without this, anyone who knows or guesses a tunnel URL
can watch a store's live camera feed.

**Team domain:** `veratori.cloudflareaccess.com`
**Identity provider:** Email OTP (Cloudflare's "One-time PIN" — built-in, no setup)
**Session duration:** 30 days

Estimated time: ~15 minutes (six near-identical Application configs).

---

## Per-franchise email allow-lists

These are the emails that can pass through Cloudflare Access to view each
franchise's camera feed.

| Franchise hostname            | Allowed emails                                                                              |
|-------------------------------|---------------------------------------------------------------------------------------------|
| `canal.cam.veratori.com`      | `felipecardozo1303@gmail.com`, `justinmeneses20@gmail.com`, `chilleddot@protonmail.com`     |
| `f43.cam.veratori.com`        | `felipecardozo1303@gmail.com`, `veratori@veratori.com`                                      |
| `f44.cam.veratori.com`        | `felipecardozo1303@gmail.com`, `veratori@veratori.com`                                      |
| `f45.cam.veratori.com`        | `felipecardozo1303@gmail.com`, `veratori@veratori.com`                                      |
| `f46.cam.veratori.com`        | `felipecardozo1303@gmail.com`, `veratori@veratori.com`                                      |
| `cam.cam.veratori.com` (demo) | `felipecardozo1303@gmail.com`, `veratori@veratori.com`                                      |

If `veratori@veratori.com` isn't a real monitored inbox, the manager won't
receive the OTP code and can't sign in. Swap for a deliverable address before
rollout.

---

## Setup steps (do this once per franchise — six applications total)

### 1. Open the Cloudflare Zero Trust dashboard

Navigate to https://one.dash.cloudflare.com → **Access** → **Applications**.

### 2. Add an application

Click **Add an application** → **Self-hosted**.

### 3. Configure the application

For Canal Street as the first example:

| Field                    | Value                                  |
|--------------------------|----------------------------------------|
| Application name         | `Veratori — Canal Street`              |
| Session Duration         | `30 days`                              |
| Application domain       | `canal.cam.veratori.com`               |
| Identity providers       | Leave "One-time PIN" checked (default) |

Leave everything else default. Click **Next**.

### 4. Configure the access policy

| Field           | Value                                                                                  |
|-----------------|----------------------------------------------------------------------------------------|
| Policy name     | `Canal allow-list`                                                                     |
| Action          | `Allow`                                                                                |
| Session duration| `Same as application session timeout`                                                  |
| Include         | **Emails** → paste the Canal allow-list (one email per line)                           |

For Canal:
```
felipecardozo1303@gmail.com
justinmeneses20@gmail.com
chilleddot@protonmail.com
```

Click **Next**.

### 5. CORS settings (CRITICAL)

In the **Setup CORS** step:

| Field                         | Value                                          |
|-------------------------------|------------------------------------------------|
| Access-Control-Allow-Credentials | **ON** (toggle on)                          |
| Access-Control-Allow-Methods  | `GET, POST, OPTIONS`                           |
| Access-Control-Allow-Origins  | `https://veratori-f3a5a.web.app`               |
| Access-Control-Allow-Headers  | `Content-Type, Authorization`                  |

Without `Allow-Credentials: ON`, the dashboard's `<img src="…/stream">` MJPEG
embeds and `fetch(..., {credentials: 'include'})` calls **will be blocked by
the browser**. This is the single most common Phase C misconfiguration.

### 6. Save & repeat

Click **Add application**. Cloudflare deploys the rule within ~30 seconds.

Repeat steps 2–6 for the remaining five hostnames, swapping in each
franchise's allow-list from the table above.

---

## Verification

After all six applications are created:

### Smoke test (unauthenticated)
```bash
curl -i https://canal.cam.veratori.com/status
```
Should respond with a **302 redirect** to a Cloudflare login URL. If you see
a JSON body, the Access policy isn't enforcing — re-check the hostname spelling.

### Smoke test (authenticated)
Open an incognito window and visit https://canal.cam.veratori.com/status.

1. You should see Cloudflare's "Sign in to … Veratori" page.
2. Enter `felipecardozo1303@gmail.com`.
3. Cloudflare sends a 6-digit code to that inbox.
4. Enter it.
5. You should be redirected to the JSON response from the camera server.
6. Cookie `CF_Authorization` is now set on `*.cam.veratori.com` for 30 days.

### End-to-end test (dashboard)

Sign in to https://veratori-f3a5a.web.app as `felipecardozo1303@gmail.com`,
then click Canal Street in the sidebar. The live MJPEG feed should load.

If you've just done the smoke test above in the same browser, no re-auth.
If you opened a fresh incognito, you'll see the Cloudflare OTP page once,
then the feed.

### Deny test
Open an incognito window in a different browser (or use a private profile
signed into a non-allowed email like a personal Gmail you haven't added).
Visit `https://canal.cam.veratori.com/status` and try to authenticate with
that other email. Cloudflare should show "you don't have permission to access
this application."

---

## Common issues

| Symptom                                    | Cause                                      | Fix                                                              |
|--------------------------------------------|--------------------------------------------|------------------------------------------------------------------|
| `<img>` stream broken after Access enabled | CORS `Allow-Credentials` is off            | Toggle it ON in the Application's CORS settings                  |
| `Allow-Origin: *` rejected by browser      | Need specific origin, not wildcard         | Set to `https://veratori-f3a5a.web.app` exactly                  |
| 401 from camera_server after OTP login     | `credentials: 'include'` missing on fetch  | Verify home.html / index.html `fetch(...)` calls send credentials|
| Cookie not set on `*.cam.veratori.com`     | Application domain typo                    | Application domain must be `canal.cam.veratori.com`, not just `cam.veratori.com` |
| OTP email never arrives                    | Allow-list email is a non-deliverable address | Swap to a monitored inbox                                     |

---

## Disabling Access (rollback)

If you need to temporarily disable a franchise's Access policy:

Zero Trust → Access → Applications → click the application → **Delete**, OR
edit the policy to add `Action: Bypass` for everyone. The tunnel returns to
publicly reachable in ~30 seconds.

This rolls Cloudflare back to where you were before this runbook. Use only
if a deployment breaks and you need to triage from the open URL.

---

## Future migration — single sign-on via Firebase OIDC

Currently each user has two login moments: signing into the dashboard
(Firebase) and answering the OTP at the Cloudflare login (one per 30 days).
A future Phase C+ migration can collapse these into one Firebase identity by
configuring Cloudflare Access with Firebase as a generic OIDC provider:

- Issuer: `https://securetoken.google.com/veratori-f3a5a`
- JWKS: `https://www.googleapis.com/service_accounts/v1/jwk/securetoken@system.gserviceaccount.com`

Not blocking. Email OTP is functionally sufficient for the first deployment.
