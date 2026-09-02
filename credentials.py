from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

# Initialize Argon2 PasswordHasher instance
_ph = PasswordHasher()

# Pre-hashed password using argon2id for 'Qx9#mK2$vL7@nR4!'
_DEMO_HASH = "$argon2id$v=19$m=65536,t=3,p=4$pLR7HllRjeJsbLQY2rWPhg$qGJicIKhkZR2djud0X35Hm/Q7wHY4jdUkfn/bU+exMg"

USERS_DB: dict[str, dict[str, str]] = {
    "Ali-datasmith": {
        "name": "Ali Datasmith",
        "password_hash": _DEMO_HASH,
    },
}


def hash_password(password: str) -> str:
    """Hashes a plaintext password using Argon2id."""
    return _ph.hash(password)


def validate_credentials(username: str, password: str) -> tuple[bool, str]:
    """Validates user credentials against stored Argon2 hashes."""
    if not username or not password:
        return False, "Username and password required."

    user_info = USERS_DB.get(username)
    if not user_info:
        return False, "Invalid credentials. Access denied."

    try:
        if _ph.verify(user_info["password_hash"], password):
            if _ph.check_needs_rehash(user_info["password_hash"]):
                user_info["password_hash"] = _ph.hash(password)
            return True, f"Welcome back, {user_info['name']}!"
    except (VerifyMismatchError, InvalidHashError):
        return False, "Invalid credentials. Access denied."

    return False, "Invalid credentials. Access denied."


def get_user_name(username: str) -> str:
    """Retrieves the display name for a given username."""
    return USERS_DB.get(username, {}).get("name", username)
