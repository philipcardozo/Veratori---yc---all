#!/usr/bin/env python3
"""
Password Hash Generation Utility
Generates bcrypt hashes for user passwords
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

try:
    from auth import generate_password_hash
except ImportError:
    print("Error: Unable to import auth module")
    print("Make sure bcrypt is installed: pip3 install bcrypt")
    sys.exit(1)

def main():
    if len(sys.argv) < 2:
        print("Password Hash Generation Utility")
        print("=" * 50)
        print("")
        print("Usage:")
        print("  python3 generate_password_hash.py <password>")
        print("")
        print("Example:")
        print("  python3 generate_password_hash.py mypassword123")
        print("")
        print("The generated hash can be used in AUTH_USERS_JSON")
        sys.exit(1)
    
    password = sys.argv[1]
    
    try:
        hash_str = generate_password_hash(password)
        print("")
        print("Generated bcrypt hash:")
        print("=" * 50)
        print(hash_str)
        print("=" * 50)
        print("")
        print("Add to AUTH_USERS_JSON like this:")
        print(f'{{"username":"{hash_str}"}}')
        print("")
    except Exception as e:
        print(f"Error generating hash: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()

