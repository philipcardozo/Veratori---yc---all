/**
 * Veratori Cloud Functions — Phase C.
 *
 * Four owner-only HTTPS-callable Functions:
 *   - setUserClaims  ({email, role, franchises[]})  → create/update a manager
 *   - listManagers   ({})                           → list non-owner users + claims
 *   - revokeUser     ({email})                      → clear claims + disable
 *   - provisionJetson({franchise_id})               → create a per-franchise Jetson identity
 *
 * Each Function verifies the caller is an owner (custom claim `role == 'owner'`
 * OR email in OWNER_EMAILS bootstrap list) before any mutation. See assertOwner().
 *
 * Frontend integration: `firebase.functions().httpsCallable('setUserClaims')(...)`.
 */

const { onCall, HttpsError } = require("firebase-functions/v2/https");
const { setGlobalOptions }   = require("firebase-functions/v2");
const admin                  = require("firebase-admin");
const crypto                 = require("crypto");

admin.initializeApp();
setGlobalOptions({ region: "us-central1", maxInstances: 10 });

// Mirrors franchise-config.js#OWNER_EMAILS. Keep in sync; this list is the
// bootstrap allow-list for the very first owner sign-in before any custom
// claims are set. Once an owner has the `role: 'owner'` custom claim, they no
// longer need to be on this list.
const OWNER_EMAILS = [
  "felipecardozo1303@gmail.com",
  "ericmendonca123@gmail.com",
];

const VALID_FRANCHISES = ["canal", "f43", "f44", "f45", "f46", "cam"];
const VALID_ROLES      = ["owner", "manager"];


// ── Helpers ──────────────────────────────────────────────────────────────────

/** Assert the caller is signed in as an owner. Throws HttpsError otherwise. */
function assertOwner(request) {
  const auth = request.auth;
  if (!auth) throw new HttpsError("unauthenticated", "Sign in required.");

  const token  = auth.token || {};
  const email  = (token.email || "").toLowerCase();
  const isOwnerByClaim = token.role === "owner";
  const isOwnerByList  = OWNER_EMAILS.map(e => e.toLowerCase()).includes(email);

  if (!isOwnerByClaim && !isOwnerByList) {
    throw new HttpsError("permission-denied", "Owner role required.");
  }
}

/** Generate a 24-char URL-safe password for Jetson identities. */
function generatePassword() {
  return crypto.randomBytes(18).toString("base64url");
}

/** Validate franchise array; throws on bad input. */
function validateFranchises(franchises, allowEmpty = false) {
  if (!Array.isArray(franchises)) {
    throw new HttpsError("invalid-argument", "franchises must be an array.");
  }
  if (!allowEmpty && franchises.length === 0) {
    throw new HttpsError("invalid-argument", "franchises cannot be empty.");
  }
  for (const f of franchises) {
    if (!VALID_FRANCHISES.includes(f)) {
      throw new HttpsError("invalid-argument", `Unknown franchise id: ${f}`);
    }
  }
}


// ── setUserClaims ────────────────────────────────────────────────────────────
//
// Create or update a manager. If the user does not exist, create them and
// trigger Firebase's built-in password-reset email so they pick their own
// password on first sign-in.
//
// Input:  { email: string, role: 'manager'|'owner', franchises: string[],
//           password?: string }  // if omitted, generated + reset link returned
// Output: { uid, created: boolean, claimsSet: object, resetLink: string|null }
exports.setUserClaims = onCall(async (request) => {
  assertOwner(request);

  const { email, role, franchises, password } = request.data || {};
  if (!email || typeof email !== "string") {
    throw new HttpsError("invalid-argument", "email is required.");
  }
  if (!VALID_ROLES.includes(role)) {
    throw new HttpsError("invalid-argument", `role must be one of ${VALID_ROLES.join(", ")}.`);
  }
  validateFranchises(franchises, /* allowEmpty */ role === "owner");

  const auth = admin.auth();
  let user, created = false;

  try {
    user = await auth.getUserByEmail(email);
  } catch (e) {
    if (e.code !== "auth/user-not-found") throw e;
    // New user: use supplied password if given (starter password flow), else
    // generate a random one and rely on the password-reset link below.
    user = await auth.createUser({
      email,
      password: (typeof password === "string" && password.length >= 6)
        ? password
        : generatePassword(),
      emailVerified: false,
      disabled: false,
    });
    created = true;
  }

  const claims = { role, franchises: role === "owner" ? [] : franchises };
  await auth.setCustomUserClaims(user.uid, claims);

  // For new users, generate a password-reset link so they pick their own.
  // We rely on Firebase to send the email via its built-in template
  // (Auth → Templates → Password reset, customizable from the console).
  let resetLink = null;
  if (created) {
    try {
      resetLink = await auth.generatePasswordResetLink(email);
      // generatePasswordResetLink does NOT auto-send — that's handled by
      // Firebase Auth when the user requests a reset. For invitations, we
      // attach the link to the response so the team panel can display it
      // (owner can also forward manually if email delivery is flaky).
    } catch (e) {
      console.warn("Could not generate reset link:", e.message);
    }
  }

  return {
    uid: user.uid,
    email: user.email,
    created,
    claimsSet: claims,
    resetLink, // null when user already existed
  };
});


// ── listManagers ─────────────────────────────────────────────────────────────
//
// Return every non-owner user with their claims + last-sign-in time.
// Owners are included with role: 'owner'.
//
// Input:  {}
// Output: { users: [{ email, uid, role, franchises, disabled, lastSignIn }, ...] }
exports.listManagers = onCall(async (request) => {
  assertOwner(request);

  const auth = admin.auth();
  const users = [];
  let pageToken;
  do {
    const res = await auth.listUsers(1000, pageToken);
    for (const u of res.users) {
      const claims = u.customClaims || {};
      users.push({
        uid:         u.uid,
        email:       u.email,
        role:        claims.role || "manager",
        franchises:  claims.franchises || [],
        disabled:    u.disabled,
        lastSignIn:  u.metadata?.lastSignInTime || null,
        created:     u.metadata?.creationTime  || null,
      });
    }
    pageToken = res.pageToken;
  } while (pageToken);

  users.sort((a, b) => (a.email || "").localeCompare(b.email || ""));
  return { users };
});


// ── revokeUser ───────────────────────────────────────────────────────────────
//
// Clear all custom claims, disable the user, and invalidate existing refresh
// tokens so any active session terminates within ~1 hour (sooner if the SDK
// retries with the revoked refresh token).
//
// Input:  { email: string }
// Output: { uid, revoked: true }
exports.revokeUser = onCall(async (request) => {
  assertOwner(request);

  const { email } = request.data || {};
  if (!email || typeof email !== "string") {
    throw new HttpsError("invalid-argument", "email is required.");
  }

  // Safety: do NOT allow an owner to lock themselves out.
  if (email.toLowerCase() === (request.auth?.token?.email || "").toLowerCase()) {
    throw new HttpsError("failed-precondition", "Cannot revoke yourself.");
  }

  const auth = admin.auth();
  const user = await auth.getUserByEmail(email);

  await auth.setCustomUserClaims(user.uid, null);
  await auth.updateUser(user.uid, { disabled: true });
  await auth.revokeRefreshTokens(user.uid);

  return { uid: user.uid, revoked: true };
});


// ── provisionJetson ──────────────────────────────────────────────────────────
//
// Create a per-franchise Jetson identity. The returned credentials get copied
// (out-of-band) into /etc/veratori/jetson-auth.env on that franchise's Jetson.
//
// The Jetson signs in to Firebase via REST as this user, gets an ID token with
// custom claim {role: 'jetson', franchise: '<id>'}, and uses it to write
// scoped data through Firestore rules.
//
// The password is returned ONCE — the owner is responsible for copying it
// before navigating away. If lost, calling provisionJetson again rotates the
// password (overwrites the existing user).
//
// Input:  { franchise_id: string }
// Output: { email, password, project_id, web_api_key }
exports.provisionJetson = onCall(async (request) => {
  assertOwner(request);

  const { franchise_id } = request.data || {};
  if (!franchise_id || !VALID_FRANCHISES.includes(franchise_id)) {
    throw new HttpsError("invalid-argument",
      `franchise_id must be one of ${VALID_FRANCHISES.join(", ")}.`);
  }

  const auth     = admin.auth();
  const email    = `jetson-${franchise_id}@bot.veratori.local`;
  const password = generatePassword();

  let user;
  try {
    user = await auth.getUserByEmail(email);
    // Existing user → rotate password.
    await auth.updateUser(user.uid, { password, emailVerified: true, disabled: false });
  } catch (e) {
    if (e.code !== "auth/user-not-found") throw e;
    user = await auth.createUser({
      email,
      password,
      emailVerified: true, // synthetic email; we mark verified to skip the flow
      disabled: false,
    });
  }

  await auth.setCustomUserClaims(user.uid, {
    role:      "jetson",
    franchise: franchise_id,
  });

  return {
    email,
    password,
    project_id:  process.env.GCLOUD_PROJECT || "veratori-f3a5a",
    // Web API key is needed to call the Identity Toolkit REST endpoint.
    // It's not a secret (it's in the frontend firebaseConfig already) but
    // we surface it here so the owner doesn't have to dig.
    web_api_key: "AIzaSyBTBYkalSjJBQjOZYetfySmG9ByEgWCcJo",
  };
});
