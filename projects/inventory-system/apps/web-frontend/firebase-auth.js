const firebaseConfig = {
  apiKey: "AIzaSyBTBYkalSjJBQjOZYetfySmG9ByEgWCcJo",
  authDomain: "veratori-f3a5a.firebaseapp.com",
  projectId: "veratori-f3a5a",
  storageBucket: "veratori-f3a5a.firebasestorage.app",
  messagingSenderId: "856326715875",
  appId: "1:856326715875:web:c9f191acde64da90d208d6",
  measurementId: "G-YS9D28SV0C"
};

if (!firebase.apps.length) firebase.initializeApp(firebaseConfig);

// Hide the page body until Firebase confirms a signed-in user. Without this
// step the protected page paints first and then redirects, which briefly
// exposes its content (and lets a fast script scrape data via the running
// JS). The visibility:hidden style is set immediately on the <html> root so
// it takes effect before any other element renders.
(function installAuthFlashGuard() {
  if (window.location.pathname.endsWith('login.html')) return; // login page renders normally
  const style = document.createElement('style');
  style.id = 'veratori-auth-flash-guard';
  style.textContent = 'html { visibility: hidden !important; }';
  (document.head || document.documentElement).appendChild(style);
})();

function _revealPage() {
  const guard = document.getElementById('veratori-auth-flash-guard');
  if (guard) guard.remove();
}

function requireAuth() {
  firebase.auth().onAuthStateChanged(user => {
    if (!user) {
      window.location.replace('login.html');
    } else {
      window.currentUser = user;
      _revealPage();
    }
  });
}

// Shared sign-out used by all pages.
function handleLogout() {
  firebase.auth().signOut().then(() => { window.location.href = 'login.html'; });
}
