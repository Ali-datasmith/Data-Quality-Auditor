from typing import Dict, Tuple
import hashlib


# ---------------------------------------------------------------------------
# Single User Store
# ---------------------------------------------------------------------------

USERS_DB: Dict[str, Dict[str, str]] = {
    "Ali-datasmith": {
        "name": "Ali Datasmith",
        "password_hash": "9cab649e5d1529a9413a51dab1e4bf50eb6b39d06cfd44874c89aeb28d613b98",
    },
}


# ---------------------------------------------------------------------------
# Hash + Validate
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def validate_credentials(username: str, password: str) -> Tuple[bool, str]:
    if not username or not password:
        return False, "Username and password required."

    if username not in USERS_DB:
        return False, "Invalid credentials. Access denied."

    if hash_password(password) != USERS_DB[username]["password_hash"]:
        return False, "Invalid credentials. Access denied."

    return True, f"Welcome back, {USERS_DB[username]['name']}!"


def get_user_name(username: str) -> str:
    return USERS_DB.get(username, {}).get("name", username)


# ---------------------------------------------------------------------------
# Credentials
# ---------------------------------------------------------------------------
# Username : Ali-datasmith
# Password : Qx9#mK2$vL7@nR4!
# ---------------------------------------------------------------------------
