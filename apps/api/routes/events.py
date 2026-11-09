from uuid import UUID

from fastapi import APIRouter, status
from pydantic import BaseModel, Field

from apps.api.dependencies import DbSession, ProjectDependency
from apps.modules.webhooks.service import IngestEventCommand, ingest_event

router = APIRouter(prefix="/events", tags=["events"])


class EventInput(BaseModel):
    event_type: str = Field(min_length=1, max_length=120, pattern=r"^[a-zA-Z0-9._-]+$")
    idempotency_key: str = Field(min_length=1, max_length=255)
    payload: dict[str, object]


class EventAccepted(BaseModel):
    event_id: UUID
    status: str
    received_at: str
    duplicate: bool


@router.post("", response_model=EventAccepted, status_code=status.HTTP_202_ACCEPTED)
def create_event(
    body: EventInput,
    db: DbSession,
    project: ProjectDependency,
) -> EventAccepted:
    event, duplicate = ingest_event(
        db,
        IngestEventCommand(
            project_id=project.id,
            event_type=body.event_type,
            idempotency_key=body.idempotency_key,
            payload=body.payload,
        ),
    )
    return EventAccepted(
        event_id=event.id,
        status="accepted",
        received_at=event.received_at.isoformat(),
        duplicate=duplicate,
    )
