#!/usr/bin/env python3
"""
One-off provisioning script for the initial Veratori dashboard users.

Run this once after Firebase Blaze is enabled. Creates the three manager
accounts with the starter password `386Canalstreet!` and the correct custom
claims so they see only their assigned franchises when they sign in to the
dashboard at https://veratori-f3a5a.web.app.

The script is idempotent:
  - If a user already exists, their password is NOT overwritten — only the
    custom claims are refreshed.
  - To force-rotate a password, delete the user from Firebase Auth first
    or use Firebase Console → Auth → Users.

Usage (from repo root):
    python3 projects/inventory-system/scripts/provision_initial_users.py

Requires the local admin SDK key at:
    projects/inventory-system/veratori-f3a5a-firebase-adminsdk-fbsvc-c3cabf3e11.json

Note on password security: `386Canalstreet!` is a STARTER credential, not a
long-term secret. Each manager should change their password on first sign-in
via the Firebase password-reset flow (forgot-password link on login.html).
"""

import sys
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, auth

CRED_PATH = (
    Path(__file__).resolve().parents[1]
    / "veratori-f3a5a-firebase-adminsdk-fbsvc-c3cabf3e11.json"
)
STARTER_PASSWORD = "386Canalstreet!"

USERS = [
    {
        "email":      "veratori@veratori.com",
        "role":       "manager",
        "franchises": ["f43", "f44", "f45", "f46", "cam"],
    },
    {
        "email":      "justinmeneses20@gmail.com",
        "role":       "manager",
        "franchises": ["canal"],
    },
    {
        "email":      "chilleddot@protonmail.com",
        "role":       "manager",
        "franchises": ["canal"],
    },
]


def ensure_user(email: str, password: str):
    """Create the user if missing, return (user_record, created_bool)."""
    try:
        user = auth.get_user_by_email(email)
        return user, False
    except auth.UserNotFoundError:
        user = auth.create_user(
            email=email,
            password=password,
            email_verified=False,
            disabled=False,
        )
        return user, True


def main() -> None:
    if not CRED_PATH.exists():
        sys.exit(f"Service account key not found at {CRED_PATH}")

    firebase_admin.initialize_app(credentials.Certificate(str(CRED_PATH)))

    print(f"Provisioning {len(USERS)} initial dashboard users …\n")

    for u in USERS:
        user, created = ensure_user(u["email"], STARTER_PASSWORD)
        tag = "created" if created else "exists "
        print(f"  [{tag}] {u['email']:<36} uid={user.uid}")

        auth.set_custom_user_claims(user.uid, {
            "role":       u["role"],
            "franchises": u["franchises"],
        })
        print(f"            role={u['role']:<7}  franchises={u['franchises']}")

    print("\nDone. New users sign in at https://veratori-f3a5a.web.app/login.html")
    print(f"with starter password: {STARTER_PASSWORD}")
    print("They should change it on first sign-in (Forgot password link).")


if __name__ == "__main__":
    main()
