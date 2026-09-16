import base64
import hashlib
import hmac
import os
import secrets
import time

from backend.config import get_settings

HASH_ALGORITHM = "pbkdf2_sha256"
HASH_ITERATIONS = 210_000
TOKEN_TTL_SECONDS = 60 * 60 * 8


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, HASH_ITERATIONS
    )
    return f"{HASH_ALGORITHM}${HASH_ITERATIONS}${_b64encode(salt)}${_b64encode(digest)}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations_text, salt_text, digest_text = password_hash.split("$", 3)
        if algorithm != HASH_ALGORITHM:
            return False
        iterations = int(iterations_text)
        salt = _b64decode(salt_text)
        expected = _b64decode(digest_text)
    except (ValueError, TypeError):
        return False
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(actual, expected)


def _signature(message: str) -> str:
    secret_key = get_settings().secret_key.encode("utf-8")
    digest = hmac.new(secret_key, message.encode("utf-8"), hashlib.sha256).digest()
    return _b64encode(digest)


def create_admin_token(admin_id: int, username: str) -> str:
    expires_at = int(time.time()) + TOKEN_TTL_SECONDS
    nonce = secrets.token_urlsafe(12)
    payload = f"{admin_id}:{username}:{expires_at}:{nonce}"
    return f"{_b64encode(payload.encode('utf-8'))}.{_signature(payload)}"


def verify_admin_token(token: str) -> tuple[int, str]:
    try:
        payload_text, signature = token.split(".", 1)
        payload = _b64decode(payload_text).decode("utf-8")
        admin_id_text, username, expires_text, _nonce = payload.split(":", 3)
        expires_at = int(expires_text)
        admin_id = int(admin_id_text)
    except (ValueError, UnicodeDecodeError):
        raise ValueError("Invalid token") from None
    if expires_at < int(time.time()):
        raise ValueError("Token expired")
    if not hmac.compare_digest(signature, _signature(payload)):
        raise ValueError("Invalid token")
    return admin_id, username
