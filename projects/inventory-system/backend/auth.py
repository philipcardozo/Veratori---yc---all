"""
Authentication Module
Provides secure session-based authentication with bcrypt password hashing
"""

import hashlib
import hmac
import json
import logging
import os
import time
from typing import Optional, Dict, Tuple
import base64

logger = logging.getLogger(__name__)

# Try to import bcrypt, provide fallback
try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False
    logger.warning("bcrypt not available, password verification will be limited")


class AuthenticationError(Exception):
    """Authentication-related errors"""
    pass


class SessionManager:
    """
    Manages secure session tokens with HMAC signing
    Sessions are stateless and contain: username, issued_at, expires_at
    """
    
    def __init__(self, secret: str, ttl_seconds: int = 86400):
        """
        Initialize session manager
        
        Args:
            secret: Secret key for HMAC signing (32+ characters recommended)
            ttl_seconds: Session time-to-live in seconds (default: 24 hours)
        """
        if not secret or len(secret) < 16:
            raise AuthenticationError("Session secret must be at least 16 characters")
        
        self.secret = secret.encode('utf-8')
        self.ttl_seconds = ttl_seconds
        
        logger.info(f"Session manager initialized: TTL={ttl_seconds}s")
    
    def create_session(self, username: str) -> str:
        """
        Create a signed session token
        
        Args:
            username: Username for the session
            
        Returns:
            Signed session token (base64 encoded)
        """
        current_time = time.time()
        expires_at = current_time + self.ttl_seconds
        
        # Create session payload
        payload = {
            'username': username,
            'issued_at': current_time,
            'expires_at': expires_at
        }
        
        # Convert to JSON and encode
        payload_json = json.dumps(payload, separators=(',', ':'))
        payload_bytes = payload_json.encode('utf-8')
        payload_b64 = base64.urlsafe_b64encode(payload_bytes).decode('utf-8')
        
        # Create HMAC signature
        signature = hmac.new(
            self.secret,
            payload_b64.encode('utf-8'),
            hashlib.sha256
        ).digest()
        signature_b64 = base64.urlsafe_b64encode(signature).decode('utf-8')
        
        # Combine payload and signature
        token = f"{payload_b64}.{signature_b64}"
        
        logger.info(f"Session created for user: {username}")
        return token
    
    def verify_session(self, token: str) -> Optional[Dict]:
        """
        Verify and decode a session token
        
        Args:
            token: Session token to verify
            
        Returns:
            Session payload dict if valid, None otherwise
        """
        try:
            # Split token into payload and signature
            parts = token.split('.')
            if len(parts) != 2:
                logger.debug("Invalid token format")
                return None
            
            payload_b64, signature_b64 = parts
            
            # Verify signature
            expected_signature = hmac.new(
                self.secret,
                payload_b64.encode('utf-8'),
                hashlib.sha256
            ).digest()
            expected_signature_b64 = base64.urlsafe_b64encode(expected_signature).decode('utf-8')
            
            if not hmac.compare_digest(signature_b64, expected_signature_b64):
                logger.warning("Invalid session signature")
                return None
            
            # Decode payload
            payload_bytes = base64.urlsafe_b64decode(payload_b64.encode('utf-8'))
            payload_json = payload_bytes.decode('utf-8')
            payload = json.loads(payload_json)
            
            # Check expiration
            current_time = time.time()
            if current_time > payload['expires_at']:
                logger.debug(f"Session expired for user: {payload['username']}")
                return None
            
            return payload
        
        except Exception as e:
            logger.debug(f"Session verification failed: {e}")
            return None
    
    def get_username_from_session(self, token: str) -> Optional[str]:
        """
        Extract username from a valid session token
        
        Args:
            token: Session token
            
        Returns:
            Username if session is valid, None otherwise
        """
        session = self.verify_session(token)
        return session['username'] if session else None


class AuthManager:
    """
    Manages user authentication with bcrypt password hashing
    """
    
    def __init__(self, users: Dict[str, str], session_secret: str, session_ttl: int = 86400):
        """
        Initialize authentication manager
        
        Args:
            users: Dictionary mapping usernames to bcrypt password hashes
            session_secret: Secret for session signing
            session_ttl: Session time-to-live in seconds
        """
        if not users:
            raise AuthenticationError("No users configured")
        
        self.users = users
        self.session_manager = SessionManager(session_secret, session_ttl)
        
        logger.info(f"Authentication manager initialized: {len(users)} users configured")
    
    def verify_password(self, username: str, password: str) -> bool:
        """
        Verify username and password
        
        Args:
            username: Username to verify
            password: Plain text password to verify
            
        Returns:
            True if credentials are valid, False otherwise
        """
        if username not in self.users:
            logger.warning(f"Login attempt for unknown user: {username}")
            return False
        
        stored_hash = self.users[username]
        
        # Verify using bcrypt
        if BCRYPT_AVAILABLE:
            try:
                # bcrypt expects bytes
                password_bytes = password.encode('utf-8')
                hash_bytes = stored_hash.encode('utf-8')
                
                if bcrypt.checkpw(password_bytes, hash_bytes):
                    logger.info(f"Successful login: {username}")
                    return True
                else:
                    logger.warning(f"Failed login attempt: {username}")
                    return False
            
            except Exception as e:
                logger.error(f"Password verification error: {e}")
                return False
        else:
            # Fallback: direct comparison (not recommended for production)
            logger.warning("Using fallback password verification (bcrypt not available)")
            if stored_hash == password:
                logger.info(f"Successful login (fallback): {username}")
                return True
            else:
                logger.warning(f"Failed login attempt (fallback): {username}")
                return False
    
    def authenticate(self, username: str, password: str) -> Optional[str]:
        """
        Authenticate user and create session
        
        Args:
            username: Username
            password: Plain text password
            
        Returns:
            Session token if authentication succeeds, None otherwise
        """
        if self.verify_password(username, password):
            return self.session_manager.create_session(username)
        return None
    
    def verify_session(self, token: str) -> Optional[str]:
        """
        Verify session token and return username
        
        Args:
            token: Session token
            
        Returns:
            Username if session is valid, None otherwise
        """
        return self.session_manager.get_username_from_session(token)

    def change_password(self, username: str, current_password: str, new_password: str) -> Tuple[bool, str]:
        """
        Change password for a user after verifying the current password.

        Args:
            username: Username whose password to change
            current_password: Current plaintext password for verification
            new_password: New plaintext password

        Returns:
            Tuple of (success, message)
        """
        if username not in self.users:
            return False, "User not found"

        if not self.verify_password(username, current_password):
            return False, "Current password is incorrect"

        if len(new_password) < 8:
            return False, "New password must be at least 8 characters"

        if BCRYPT_AVAILABLE:
            new_hash = generate_password_hash(new_password)
        else:
            new_hash = new_password

        self.users[username] = new_hash
        logger.info(f"Password changed for user: {username}")
        return True, "Password changed successfully"


def load_auth_config() -> Tuple[bool, Optional[AuthManager]]:
    """
    Load authentication configuration from environment variables
    
    Returns:
        Tuple of (enabled, auth_manager)
        - enabled: Whether authentication is enabled
        - auth_manager: AuthManager instance if enabled and configured, None otherwise
    """
    # Check if authentication is enabled
    auth_enabled = os.getenv('AUTH_ENABLED', 'true').lower() == 'true'
    
    if not auth_enabled:
        logger.info("Authentication disabled via AUTH_ENABLED=false")
        return False, None
    
    # Load session secret
    session_secret = os.getenv('AUTH_SESSION_SECRET')
    if not session_secret:
        logger.error("AUTH_SESSION_SECRET not configured - authentication cannot be enabled")
        logger.error("Generate a secret with: python3 -c 'import secrets; print(secrets.token_urlsafe(32))'")
        return True, None  # Enabled but not configured = deny access
    
    # Load session TTL
    try:
        session_ttl = int(os.getenv('AUTH_SESSION_TTL', '86400'))
    except ValueError:
        logger.warning("Invalid AUTH_SESSION_TTL, using default 86400")
        session_ttl = 86400
    
    # Load users from JSON
    users_json = os.getenv('AUTH_USERS_JSON')
    if not users_json:
        logger.error("AUTH_USERS_JSON not configured - no users available")
        return True, None  # Enabled but not configured = deny access
    
    try:
        users = json.loads(users_json)
        if not users or not isinstance(users, dict):
            logger.error("AUTH_USERS_JSON must be a non-empty JSON object")
            return True, None
        
        # Create auth manager
        auth_manager = AuthManager(users, session_secret, session_ttl)
        return True, auth_manager
    
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse AUTH_USERS_JSON: {e}")
        return True, None
    except AuthenticationError as e:
        logger.error(f"Failed to initialize authentication: {e}")
        return True, None


def generate_password_hash(password: str) -> str:
    """
    Generate bcrypt hash for a password
    
    Args:
        password: Plain text password
        
    Returns:
        Bcrypt hash string
    """
    if not BCRYPT_AVAILABLE:
        raise RuntimeError("bcrypt is required to generate password hashes")
    
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt(rounds=12)
    hash_bytes = bcrypt.hashpw(password_bytes, salt)
    return hash_bytes.decode('utf-8')


# Example usage for generating hashes
if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'generate-hash':
        if len(sys.argv) != 3:
            print("Usage: python3 auth.py generate-hash <password>")
            sys.exit(1)
        
        password = sys.argv[2]
        hash_str = generate_password_hash(password)
        print(f"Bcrypt hash: {hash_str}")
    else:
        print("Authentication module")
        print("Usage: python3 auth.py generate-hash <password>")

