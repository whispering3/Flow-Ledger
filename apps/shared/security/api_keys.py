import hashlib
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.modules.projects.models import ApiKey, Project


def hash_api_key(raw_key: str) -> str:
    """Keys are high-entropy credentials; retain only their SHA-256 digest."""
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def authenticate_api_key(session: Session, raw_key: str) -> Project | None:
    api_key = session.scalar(select(ApiKey).where(ApiKey.key_hash == hash_api_key(raw_key)))
    if api_key is None or api_key.revoked_at is not None:
        return None
    if api_key.expires_at is not None and api_key.expires_at <= datetime.now(UTC):
        return None
    return session.get(Project, api_key.project_id)
