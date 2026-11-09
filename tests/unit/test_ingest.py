from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from apps.api.database import Base
from apps.modules.destinations.models import Destination  # noqa: F401
from apps.modules.executions.models import Execution  # noqa: F401
from apps.modules.organizations.models import Organization
from apps.modules.projects.models import Project
from apps.modules.webhooks.models import Event, OutboxMessage
from apps.modules.webhooks.service import IngestEventCommand, ingest_event


def test_ingestion_is_idempotent_and_creates_one_outbox_message() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        organization = Organization(name="Acme", slug="acme")
        session.add(organization)
        session.flush()
        project = Project(organization_id=organization.id, name="Billing")
        session.add(project)
        session.commit()

        command = IngestEventCommand(
            project_id=project.id,
            event_type="payment.approved",
            idempotency_key="payment-123",
            payload={"payment_id": "123"},
        )
        event, duplicate = ingest_event(session, command)
        repeated_event, repeated_duplicate = ingest_event(session, command)

        assert duplicate is False
        assert repeated_duplicate is True
        assert repeated_event.id == event.id
        assert len(session.scalars(select(Event)).all()) == 1
        assert len(session.scalars(select(OutboxMessage)).all()) == 1
