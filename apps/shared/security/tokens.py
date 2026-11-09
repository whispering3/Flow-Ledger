import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt

from apps.api.config import get_settings

ACCESS_TOKEN_MINUTES = 15
REFRESH_TOKEN_DAYS = 30


def create_access_token(user_id: UUID) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": str(user_id),
            "type": "access",
            "iat": now,
            "exp": now + timedelta(minutes=ACCESS_TOKEN_MINUTES),
        },
        get_settings().jwt_secret,
        algorithm="HS256",
    )


def parse_access_token(raw_token: str) -> UUID | None:
    try:
        claims = jwt.decode(raw_token, get_settings().jwt_secret, algorithms=["HS256"])
        if claims.get("type") != "access":
            return None
        return UUID(claims["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        return None


def create_refresh_token() -> str:
    return f"flr_{secrets.token_urlsafe(48)}"


def hash_refresh_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
