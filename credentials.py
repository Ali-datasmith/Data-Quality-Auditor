import hashlib
from typing import Any

_ph: Any = None
_ARGON2_AVAILABLE = False

try:
    from argon2 import PasswordHasher
    from argon2.exceptions import InvalidHashError, VerifyMismatchError
    _ARGON2_AVAILABLE = True
    _ph = PasswordHasher()
except ImportError:
    _ARGON2_AVAILABLE = False
    _ph = None

# Pre-hashed password using argon2id for 'Qx9#mK2$vL7@nR4!'
_DEMO_HASH = "$argon2id$v=19$m=65536,t=3,p=4$pLR7HllRjeJsbLQY2rWPhg$qGJicIKhkZR2djud0X35Hm/Q7wHY4jdUkfn/bU+exMg"
# Static salt and PBKDF2 hash for fallback verification
_SALT = b"auditor_salt_2026"
_FALLBACK_PBKDF2_HASH = "1ca4f324cbce7bac9ecd7b9978305e4ea8f17d679850923e1cd057b7e1f777bf"

USERS_DB: dict[str, dict[str, str]] = {
    "Ali-datasmith": {
        "name": "Ali Datasmith",
        "password_hash": _DEMO_HASH,
        "pbkdf2_hash": _FALLBACK_PBKDF2_HASH,
    },
}


def _hash_pbkdf2(password: str) -> str:
    """Computes a key-stretched PBKDF2-HMAC-SHA256 digest for password hashing."""
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        _SALT,
        iterations=100000,
    ).hex()


def hash_password(password: str) -> str:
    """Hashes a plaintext password using Argon2id if available, fallback to key-stretched PBKDF2."""
    if _ARGON2_AVAILABLE and _ph is not None:
        return str(_ph.hash(password))
    return _hash_pbkdf2(password)


def validate_credentials(username: str, password: str) -> tuple[bool, str]:
    """Validates user credentials against stored Argon2 hashes (or fallback PBKDF2)."""
    if not username or not password:
        return False, "Username and password required."

    user_info = USERS_DB.get(username)
    if not user_info:
        return False, "Invalid credentials. Access denied."

    if _ARGON2_AVAILABLE and _ph is not None:
        try:
            if _ph.verify(user_info["password_hash"], password):
                if _ph.check_needs_rehash(user_info["password_hash"]):
                    user_info["password_hash"] = str(_ph.hash(password))
                return True, f"Welcome back, {user_info['name']}!"
        except (VerifyMismatchError, InvalidHashError):
            return False, "Invalid credentials. Access denied."
    else:
        input_hash = _hash_pbkdf2(password)
        if input_hash == user_info.get("pbkdf2_hash"):
            return True, f"Welcome back, {user_info['name']}!"

    return False, "Invalid credentials. Access denied."


def get_user_name(username: str) -> str:
    """Retrieves the display name for a given username."""
    return USERS_DB.get(username, {}).get("name", username)
