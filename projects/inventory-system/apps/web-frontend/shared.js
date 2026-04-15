/* ================================================================
   Veratori — Shared JS Utilities
   Sidebar management, safe API fetching, common helpers.
   ================================================================ */

// ---- Sidebar ----
(function initSidebar() {
    const menuBtn    = document.getElementById('menuBtn');
    const sidebar    = document.getElementById('sidebar');
    const overlay    = document.getElementById('sidebarOverlay');
    const closeBtn   = document.getElementById('sidebarClose');

    if (!menuBtn || !sidebar) return;

    function open()  { sidebar.classList.add('open');    overlay?.classList.add('active'); }
    function close() { sidebar.classList.remove('open'); overlay?.classList.remove('active'); }

    menuBtn.addEventListener('click', open);
    closeBtn?.addEventListener('click', close);
    overlay?.addEventListener('click', close);

    // Close on Escape
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && sidebar.classList.contains('open')) close();
    });
})();


// ---- Safe Fetch with JSON Validation ----
/**
 * Wrapper around fetch that:
 *  1. Sends credentials (same-origin)
 *  2. Redirects to login on 401
 *  3. Validates the response is JSON before parsing
 *
 * @param {string} url
 * @param {RequestInit} options
 * @returns {Promise<any>} parsed JSON body
 */
async function apiFetch(url, options = {}) {
    const defaults = { credentials: 'same-origin' };
    const res = await fetch(url, { ...defaults, ...options });

    if (res.status === 401) {
        window.location.href = 'login.html';
        throw new Error('Unauthorized');
    }

    const ct = res.headers.get('content-type') || '';
    if (!ct.includes('application/json')) {
        const text = await res.text();
        throw new Error(
            `Expected JSON response but received ${ct || 'unknown'}.\n` +
            (text.length > 200 ? text.slice(0, 200) + '…' : text)
        );
    }

    return res.json();
}

