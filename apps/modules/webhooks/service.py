from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from apps.modules.webhooks.models import Event, EventStatus, OutboxMessage, OutboxStatus


@dataclass(frozen=True)
class IngestEventCommand:
    project_id: UUID
    event_type: str
    idempotency_key: str
    payload: dict[str, Any]


def ingest_event(session: Session, command: IngestEventCommand) -> tuple[Event, bool]:
    """Atomically persist an event and the message needed to process it."""
    # Generate it before adding the models so the outbox can reference the
    # exact same aggregate ID within this transaction.
    event_id = uuid4()
    event = Event(
        id=event_id,
        project_id=command.project_id,
        event_type=command.event_type,
        idempotency_key=command.idempotency_key,
        payload=command.payload,
        status=EventStatus.QUEUED,
    )
    outbox = OutboxMessage(
        aggregate_id=event_id,
        topic="webhook.event.accepted.v1",
        payload={"event_id": str(event.id), "project_id": str(command.project_id)},
        status=OutboxStatus.PENDING,
    )
    try:
        session.add_all((event, outbox))
        session.commit()
        session.refresh(event)
        return event, False
    except IntegrityError:
        session.rollback()
        existing = session.scalar(
            select(Event).where(
                Event.project_id == command.project_id,
                Event.idempotency_key == command.idempotency_key,
            )
        )
        if existing is None:
            raise
        return existing, True
