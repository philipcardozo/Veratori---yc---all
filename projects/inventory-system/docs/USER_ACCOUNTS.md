# User Accounts & Multi-Tenant Auth

Quick reference for who has access to what and how to provision new users.

## Where user data actually lives

The Veratori web app **does not maintain its own user database or password
table.** All identity is handled by **Firebase Authentication**:

- Passwords are stored by Firebase, salted + hashed with scrypt — we never
  see or store cleartext passwords.
- The user roster is visible at
  <https://console.firebase.google.com/project/veratori-f3a5a/authentication/users>
- Each user has a stable `uid`, an email, and optional **custom claims**
  (`role`, `franchises`) that we use to drive multi-tenant access control.

There is currently **no separate database** of accounts to maintain. Creating
a user in the Firebase console is the only step needed to provision one.

## Account model

| Account | Role | Sees |
|---|---|---|
| **felipecardozo1303@gmail.com** | `owner` | All 6 locations (`canal`, `f43`, `f44`, `f45`, `f46`, `cam`) |
| Canal Street manager | `manager` | `canal` only |
| 43rd Street manager | `manager` | `f43` only |
| 44th Street manager | `manager` | `f44` only |
| 45th Street manager | `manager` | `f45` only |
| 46th Street manager | `manager` | `f46` only |

Roles are enforced by `role-guard.js` on the frontend (hides forbidden
locations, redirects deep-link attempts back to the hub). Once Cloudflare
Access is wired up (Phase C), the tunnels themselves verify the role
server-side — defence in depth.

## How to create the master account (one-time)

You already have `felipecardozo1303@gmail.com` set as a bootstrap owner in
`franchise-config.js` (`window.OWNER_EMAILS`). To activate it:

1. Visit <https://veratori-f3a5a.web.app/login.html>
2. Either sign in with Google using `felipecardozo1303@gmail.com`, **or**
   click "Create Account" and register with that email + a password
3. You're done. Sign in, hit the hub, all 6 locations should appear.

## How to create a franchise manager

For each franchise:

### Step 1 — create the user in Firebase Console (1 min)

1. Open <https://console.firebase.google.com/project/veratori-f3a5a/authentication/users>
2. Click **Add user** → enter the manager's email + a temporary password
3. Email the manager: *"Visit veratori-f3a5a.web.app, click 'Forgot password?'
   and reset your password using this address."*

### Step 2 — set their role + franchise (custom claims)

Until the Cloud Function from Phase C ships, you set custom claims via the
Admin SDK from a one-off Node script. From any machine with the Firebase
Admin credentials:

```js
// scripts/set-manager-role.js
const admin = require('firebase-admin');
admin.initializeApp({ credential: admin.credential.applicationDefault() });

const TARGETS = [
  { email: 'manager-canal@veratori.com',   role: 'manager', franchises: ['canal'] },
  { email: 'manager-43rd@veratori.com',    role: 'manager', franchises: ['f43']   },
  { email: 'manager-44th@veratori.com',    role: 'manager', franchises: ['f44']   },
  { email: 'manager-45th@veratori.com',    role: 'manager', franchises: ['f45']   },
  { email: 'manager-46th@veratori.com',    role: 'manager', franchises: ['f46']   },
  { email: 'felipecardozo1303@gmail.com',  role: 'owner' },
];

(async () => {
  for (const t of TARGETS) {
    const user = await admin.auth().getUserByEmail(t.email);
    const claims = { role: t.role };
    if (t.franchises) claims.franchises = t.franchises;
    await admin.auth().setCustomUserClaims(user.uid, claims);
    console.log(`✓ ${t.email} → ${JSON.stringify(claims)}`);
  }
})();
```

Run with: `node scripts/set-manager-role.js`. Once set, the user has to
sign out and back in for the new claims to load into their ID token.

### Step 3 — verify

Have the manager sign in. Sidebar should show only their franchise.
Visiting `index.html?loc=canal` from another manager's account should
redirect them back to the hub.

## Public-access check

Without a Firebase ID token, the protected pages (`home.html`,
`index.html`, `account.html`, `analytics.html`, `ai-analytics.html`,
`upload.html`, `restock-app.html`) all redirect to `login.html` via
`requireAuth()`. An `auth-flash` guard hides the page body until Firebase
confirms a user, so no content paints before redirect.

**Caveat (closed in Phase C):** the camera server itself (`localhost:5001`
locally, `*.cam.veratori.com` once Jetsons are tunnelled) currently
returns data to anyone who knows the URL. The frontend won't show it to
unauthorised users, but `curl https://canal.cam.veratori.com/sales` would
work from any machine. Cloudflare Access — verifying a Firebase ID token
at the edge — closes this in Phase C. **Until then, treat the tunnel URLs
as semi-private** (security-through-obscurity).

## Password reset

`login.html` has a "Forgot password?" link that calls Firebase's
`sendPasswordResetEmail`. The user gets a magic link in their inbox. The
email template (subject, body, sender name) is configurable at
<https://console.firebase.google.com/project/veratori-f3a5a/authentication/emails>.

## Adding new locations later

When franchise #7 opens:

1. Add the entry to `window.FRANCHISE_CONFIG` in `franchise-config.js`
2. Deploy the frontend
3. Run `bash scripts/jetson-setup.sh f47` on the new Jetson
4. Create the manager account in Firebase Console + set their claims

Everything else picks up automatically.
