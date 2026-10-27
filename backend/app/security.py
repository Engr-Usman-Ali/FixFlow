"""Password hashing and login tokens.

Passwords (NFR-SEC-002, NFR-SEC-004)
  * A new random salt (SECRETS module, PASSWORD_SALT_BYTES long) is generated
    for every user and every password change, and stored in its own column.
  * The hash is PBKDF2-HMAC-SHA256 over (pepper + password) with that salt and
    PASSWORD_HASH_ITERATIONS rounds. The iteration count is stored per user so
    it can be raised later; older hashes are upgraded at the next sign-in.
  * The optional PASSWORD_PEPPER lives only in .env, never in the database,
    so a leaked database alone is not enough to test password guesses.
  * Hashes are compared in constant time.

Tokens
  * Signed JWT holding the user id, company id and token_version.
  * Signing out raises token_version, which makes every older token invalid.
"""
import hashlib
import hmac
import re
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt

from .config import settings

PASSWORD_RULES = (
    "Use at least {n} characters with an uppercase letter, a lowercase letter and a number."
)


@dataclass(frozen=True)
class PasswordHash:
    hash: str
    salt: str
    iterations: int


def password_problem(password: str) -> Optional[str]:
    """Return a plain-language problem with the password, or None if it is acceptable."""
    n = settings.password_min_length
    if (
        len(password) < n
        or not re.search(r"[A-Z]", password)
        or not re.search(r"[a-z]", password)
        or not re.search(r"\d", password)
    ):
        return PASSWORD_RULES.format(n=n)
    return None


def _derive(password: str, salt_hex: str, iterations: int) -> str:
    material = (settings.password_pepper + password).encode("utf-8")
    return hashlib.pbkdf2_hmac("sha256", material, bytes.fromhex(salt_hex), iterations).hex()


def hash_password(password: str) -> PasswordHash:
    salt = secrets.token_hex(settings.password_salt_bytes)
    iterations = settings.password_hash_iterations
    return PasswordHash(hash=_derive(password, salt, iterations), salt=salt, iterations=iterations)


def verify_password(password: str, stored_hash: str, salt: str, iterations: int) -> bool:
    try:
        candidate = _derive(password, salt, iterations)
    except ValueError:  # malformed salt
        return False
    return hmac.compare_digest(candidate, stored_hash)


def needs_rehash(iterations: int) -> bool:
    return iterations < settings.password_hash_iterations


# A real hash used when the email is unknown, so a failed sign-in takes the
# same time whether or not the account exists (FR-002).
_DUMMY = hash_password(secrets.token_urlsafe(16))


def burn_time(password: str) -> None:
    verify_password(password, _DUMMY.hash, _DUMMY.salt, _DUMMY.iterations)


# ------------------------------------------------------------------ tokens ---
def create_access_token(user_id: int, organization_id: int, token_version: int) -> tuple[str, datetime]:
    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(user_id),
        "org": organization_id,
        "ver": token_version,
        "iat": now,
        "exp": expires,
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm), expires


@dataclass(frozen=True)
class TokenClaims:
    user_id: int
    organization_id: int
    token_version: int


def decode_token(token: str) -> Optional[TokenClaims]:
    """Return the claims of a valid, unexpired token, otherwise None."""
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "org", "ver", "exp"]},
        )
        return TokenClaims(int(payload["sub"]), int(payload["org"]), int(payload["ver"]))
    except (jwt.PyJWTError, KeyError, ValueError, TypeError):
        return None


def new_join_code() -> str:
    """Short code employees type to join their company, e.g. 7KQ2-MX9P."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O or 1/I look-alikes
    raw = "".join(secrets.choice(alphabet) for _ in range(8))
    return f"{raw[:4]}-{raw[4:]}"
