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

function requireAuth() {
  firebase.auth().onAuthStateChanged(user => {
    if (!user) {
      window.location.replace('login.html');
    } else {
      window.currentUser = user;
    }
  });
}

// Shared sign-out used by all pages.
function handleLogout() {
  firebase.auth().signOut().then(() => { window.location.href = 'login.html'; });
}
