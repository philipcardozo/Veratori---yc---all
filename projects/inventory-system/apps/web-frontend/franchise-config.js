/* eslint-disable */
/**
 * Veratori franchise registry — single source of truth for where each franchise
 * lives on the network. Every camera/sales/report HTTP call routes through the
 * helper below, so swapping `localhost` → Cloudflare Tunnel hostname is a
 * config change instead of a code change.
 *
 *  is_local=true  → API base resolves to http://localhost:5001 (dev / demo)
 *  tunnel_host    → API base resolves to https://<tunnel_host> (production)
 *
 * IDs match home.html's FRANCHISES object so existing routing keeps working.
 */

/**
 * BOOTSTRAP OWNER LIST — Phase A only.
 *
 * Until Firebase custom claims are deployed (Phase B / C), any signed-in
 * user whose email appears here is treated as an owner. This unblocks
 * testing before the Cloud Function for setUserClaims is wired up.
 *
 * Once custom claims are live, claims take precedence over this list
 * (see role-guard.js). To remove a bootstrap owner later, just clear
 * their custom claims via the Admin SDK and delete them from this list.
 *
 * Add yourself + any other temporary owners here:
 */
window.OWNER_EMAILS = [
  'felipecardozo1303@gmail.com',
  'ericmendonca123@gmail.com',
];

window.FRANCHISE_CONFIG = {
  canal: {
    name: 'Canal Street',
    sub:  'Manhattan · Flagship',
    tunnel_host: 'canal.cam.veratori.com',
  },
  f43: {
    name: '43rd Street',
    sub:  'Midtown',
    tunnel_host: 'f43.cam.veratori.com',
  },
  f44: {
    name: '44th Street',
    sub:  'Midtown East',
    tunnel_host: 'f44.cam.veratori.com',
  },
  f45: {
    name: '45th Street',
    sub:  "Hell's Kitchen",
    tunnel_host: 'f45.cam.veratori.com',
  },
  f46: {
    name: '46th Street',
    sub:  'Times Square',
    tunnel_host: 'f46.cam.veratori.com',
  },
  // Demo franchise comes last so owners default to a real location, not the dev one.
  cam: {
    name: 'Camera Demo',
    sub:  'Local · USB Camera',
    is_local: true,
    tunnel_host: null,
  },
};

/**
 * Resolve an API base URL for a given franchise id.
 *
 *   getApiBase('cam')   → 'http://localhost:5001'   (Mac dev franchise)
 *   getApiBase('canal') → 'https://canal.cam.veratori.com'
 *   getApiBase(null)    → 'http://localhost:5001'   (legacy default)
 *
 * Override per-environment via:
 *   localStorage.setItem('veratori-api-override', 'https://staging.cam...')
 * (useful for testing a real tunnel against a single franchise without
 * rebuilding the config file).
 */
window.getApiBase = function (franchise_id) {
  const override = (() => {
    try { return localStorage.getItem('veratori-api-override'); }
    catch { return null; }
  })();
  if (override) return override;

  const cfg = window.FRANCHISE_CONFIG[franchise_id];
  if (!cfg) return 'http://localhost:5001';
  if (cfg.is_local) return 'http://localhost:5001';
  if (cfg.tunnel_host) return `https://${cfg.tunnel_host}`;
  return 'http://localhost:5001';
};

/**
 * Read the franchise id from the URL (?loc=<id>) or default to 'cam' for
 * back-compat with the existing Camera Demo dashboard URL.
 */
window.getCurrentFranchiseId = function () {
  const params = new URLSearchParams(window.location.search);
  const loc = params.get('loc');
  if (loc && window.FRANCHISE_CONFIG[loc]) return loc;
  return 'cam';
};
