from typing import Dict, Tuple
import hashlib

# ---------------------------------------------------------------------------
# Demo User Store (production: use real database)
# ---------------------------------------------------------------------------
USERS_DB: Dict[str, Dict[str, str]] = {
    "admin": {
        "name": "Admin User",
        "password_hash": "8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918",  # "admin"
    },
    "demo": {
        "name": "Demo User",
        "password_hash": "ae2b1fca515949e5d54fb22b8ed95e7f5fa3d58dacc33e7993b8d1e932a61e91",  # "demo"
    },
}

# ---------------------------------------------------------------------------
# Simple hash function (SHA-256)
# Production: use bcrypt.hashpw() instead
# ---------------------------------------------------------------------------
def hash_password(password: str) -> str:
    """
    Hash a plaintext password using SHA-256.
    For production, replace with bcrypt.hashpw()
    """
    return hashlib.sha256(password.encode()).hexdigest()

def validate_credentials(username: str, password: str) -> Tuple[bool, str]:
    """
    Validate username and password.
    
    Returns:
        (success: bool, message: str)
    """
    if not username or not password:
        return False, "Username and password required."
    
    if username not in USERS_DB:
        return False, f"User '{username}' not found."
    
    user_record = USERS_DB[username]
    password_hash = hash_password(password)
    
    if password_hash != user_record["password_hash"]:
        return False, "Incorrect password."
    
    return True, f"Welcome, {user_record['name']}!"

def get_user_name(username: str) -> str:
    """Get the display name of a user."""
    return USERS_DB.get(username, {}).get("name", username)
