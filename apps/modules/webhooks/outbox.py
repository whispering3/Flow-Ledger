from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.modules.webhooks.models import OutboxMessage, OutboxStatus

Publish = Callable[[str, dict[str, Any]], None]


def publish_pending_messages(session: Session, publish: Publish, batch_size: int = 100) -> int:
    """Publish a locked outbox message and mark it only after broker acceptance.

    A crash after `publish` but before `commit` deliberately causes a duplicate
    broker message. Consumers must therefore remain idempotent.
    """
    published_count = 0
    for _ in range(batch_size):
        message = session.scalar(
            select(OutboxMessage)
            .where(OutboxMessage.status == OutboxStatus.PENDING)
            .order_by(OutboxMessage.created_at)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if message is None:
            session.rollback()
            return published_count
        try:
            publish(message.topic, message.payload)
            message.status = OutboxStatus.PUBLISHED
            message.published_at = datetime.now(UTC)
            session.commit()
            published_count += 1
        except Exception:
            session.rollback()
            raise
    return published_count
