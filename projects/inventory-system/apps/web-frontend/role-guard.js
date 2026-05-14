/* eslint-disable */
/**
 * Multi-tenant role enforcement for the Veratori dashboard.
 *
 * Reads Firebase custom claims attached to the signed-in user and exposes
 * helpers that the rest of the frontend uses to filter what's visible.
 *
 * Expected claim shape (set via the Firebase Admin SDK):
 *   { role: 'owner' }                                  → sees all franchises
 *   { role: 'manager', franchises: ['canal'] }         → only Canal Street
 *   { role: 'manager', franchises: ['canal', 'f43'] }  → two locations
 *
 * Defensive default: a user with no `role` claim is treated as a manager
 * with zero allowed franchises (they see an empty hub) — failing closed is
 * safer than failing open. To grant access, set claims via setUserRole.
 */

window.VeratoriRole = (function () {
  let cached = null;

  async function load() {
    if (cached) return cached;
    if (typeof firebase === 'undefined' || !firebase.auth) {
      cached = { role: 'guest', franchises: [], ready: true };
      return cached;
    }
    return new Promise((resolve) => {
      firebase.auth().onAuthStateChanged(async (user) => {
        if (!user) {
          cached = { role: 'guest', franchises: [], ready: true, user: null };
          resolve(cached); return;
        }
        try {
          const tokenResult = await user.getIdTokenResult(/*forceRefresh*/ false);
          const claims = tokenResult.claims || {};

          // Bootstrap allowlist: if the user has no role claim yet but their
          // email appears in OWNER_EMAILS (defined in franchise-config.js),
          // grant owner role on the client. This unblocks Phase A testing
          // before Firebase custom claims are deployed. Real custom claims,
          // when present, take precedence.
          const owners = window.OWNER_EMAILS || [];
          const isBootstrapOwner = !claims.role && owners.includes(user.email);
          if (isBootstrapOwner) {
            console.info('[role-guard] bootstrap owner mode for', user.email);
          }

          cached = {
            role: claims.role || (isBootstrapOwner ? 'owner' : 'manager'),
            franchises: Array.isArray(claims.franchises) ? claims.franchises : [],
            email: user.email,
            uid:   user.uid,
            ready: true,
            user,
          };
        } catch (e) {
          console.warn('[role-guard] could not read claims:', e);
          cached = { role: 'manager', franchises: [], ready: true, user };
        }
        resolve(cached);
      });
    });
  }

  /** Return list of franchise ids this user is allowed to see. */
  function allowedFranchises() {
    if (!cached) return [];
    if (cached.role === 'owner') {
      return Object.keys(window.FRANCHISE_CONFIG || {});
    }
    return cached.franchises || [];
  }

  /** True if the user can access this franchise's data. */
  function canAccess(franchise_id) {
    if (!cached) return false;
    if (cached.role === 'owner') return true;
    return (cached.franchises || []).includes(franchise_id);
  }

  /** Cached, sync access. Returns null if not loaded yet. */
  function current() { return cached; }

  return { load, allowedFranchises, canAccess, current };
})();
