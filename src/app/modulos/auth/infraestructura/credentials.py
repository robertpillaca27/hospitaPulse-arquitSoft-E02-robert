"""Password hashing and signed session token helpers."""

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from app.shared.config import get_settings

JWT_ALGORITHM = "HS256"
SESSION_DURATION = timedelta(minutes=10)


class PasswordHasher:
    """Hash and verify passwords with bcrypt."""

    @staticmethod
    def hash(password: str) -> str:
        """Return a salted bcrypt hash."""
        if len(password.encode("utf-8")) > 72:
            raise ValueError("La contraseña no puede superar 72 bytes UTF-8.")
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("ascii")

    @staticmethod
    def verify(password: str, password_hash: str) -> bool:
        """Compare a candidate password to a stored bcrypt hash."""
        try:
            return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("ascii"))
        except (ValueError, UnicodeEncodeError):
            return False


def create_access_token(
    user_id: str,
    role: str | None = None,
    must_change_password: bool = False,
) -> str:
    """Sign a ten-minute HS256 session token for an active account."""
    secret = get_settings().jwt_secret
    if secret is None:
        raise RuntimeError("JWT_SECRET no está configurado.")
    now = datetime.now(timezone.utc)
    claims: dict[str, Any] = {
        "sub": user_id,
        "iat": now,
        "exp": now + SESSION_DURATION,
    }
    if role is not None:
        claims["role"] = role
        claims["must_change_password"] = must_change_password
    return jwt.encode(
        claims,
        secret,
        algorithm=JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """Verify the signature, algorithm, and expiration of an access token."""
    secret = get_settings().jwt_secret
    if secret is None:
        raise RuntimeError("JWT_SECRET no está configurado.")
    return jwt.decode(token, secret, algorithms=[JWT_ALGORITHM])
