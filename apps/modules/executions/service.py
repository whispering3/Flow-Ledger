from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from apps.modules.destinations.models import Destination
from apps.modules.executions.models import Execution, ExecutionStatus
from apps.modules.webhooks.models import Event


def materialize_executions(session: Session, event_id: UUID) -> list[Execution]:
    """Create one pending execution for every matching enabled destination.

    The unique `(event_id, destination_id)` constraint is the final guard against
    duplicate outbox publication. A nested transaction lets duplicate inserts be
    ignored without rolling back executions created for other destinations.
    """
    event = session.get(Event, event_id)
    if event is None:
        raise LookupError(f"Event {event_id} does not exist")

    destinations = session.scalars(
        select(Destination).where(
            Destination.project_id == event.project_id,
            Destination.enabled.is_(True),
        )
    ).all()
    created: list[Execution] = []
    for destination in destinations:
        if destination.event_types and event.event_type not in destination.event_types:
            continue
        execution = Execution(
            project_id=event.project_id,
            event_id=event.id,
            destination_id=destination.id,
            status=ExecutionStatus.PENDING,
        )
        try:
            with session.begin_nested():
                session.add(execution)
                session.flush()
        except IntegrityError:
            continue
        created.append(execution)
    session.commit()
    return created
