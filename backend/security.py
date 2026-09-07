"""Password hashing for the email+password login flow.

Deliberately dependency-light (stdlib `hashlib.pbkdf2_hmac`, no passlib/bcrypt) in keeping with the
rest of the project (see cipher.py's homegrown SimpleCipher). Stored format is
"<salt-hex>$<iterations>$<derived-key-hex>" so the iteration count can be raised later without
invalidating hashes created under a lower one.
"""
import hashlib
import hmac
import os

_ITERATIONS = 260_000


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERATIONS)
    return f"{salt.hex()}${_ITERATIONS}${derived.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, iterations_str, derived_hex = stored.split("$", 2)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(derived_hex)
        iterations = int(iterations_str)
    except ValueError:
        return False

    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(derived, expected)
