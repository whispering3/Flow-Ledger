from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from apps.api.database import Base
from apps.shared.security.secrets import generate_encrypted_signing_secret

json_type = JSON().with_variant(JSONB, "postgresql")


class Destination(Base):
    __tablename__ = "destinations"
    __table_args__ = (Index("ix_destinations_project_enabled", "project_id", "enabled"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    event_types: Mapped[list[str]] = mapped_column(json_type, nullable=False, default=list)
    signing_secret_ciphertext: Mapped[str] = mapped_column(
        String(512), nullable=False, default=generate_encrypted_signing_secret
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
