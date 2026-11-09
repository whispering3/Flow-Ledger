from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from apps.api.database import Base
from apps.modules.organizations.models import Organization
from apps.modules.projects.models import Project
from apps.modules.webhooks.models import Event, OutboxMessage, OutboxStatus
from apps.modules.webhooks.outbox import publish_pending_messages


def test_publisher_marks_message_only_after_publish_succeeds() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        organization = Organization(name="Acme", slug="acme")
        session.add(organization)
        session.flush()
        project = Project(organization_id=organization.id, name="Billing")
        session.add(project)
        session.flush()
        event = Event(
            project_id=project.id,
            event_type="payment.approved",
            idempotency_key="payment-123",
            payload={"payment_id": "123"},
        )
        session.add(event)
        session.flush()
        message = OutboxMessage(
            aggregate_id=event.id,
            topic="webhook.event.accepted.v1",
            payload={"event_id": str(event.id)},
        )
        session.add(message)
        session.commit()

        calls: list[tuple[str, dict[str, object]]] = []
        published = publish_pending_messages(
            session, lambda topic, payload: calls.append((topic, payload))
        )
        assert published == 1
        assert calls == [("webhook.event.accepted.v1", {"event_id": str(event.id)})]
        assert session.scalar(select(OutboxMessage)).status == OutboxStatus.PUBLISHED


def test_failed_publish_leaves_outbox_message_pending() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        organization = Organization(name="Acme", slug="acme")
        session.add(organization)
        session.flush()
        project = Project(organization_id=organization.id, name="Billing")
        session.add(project)
        session.flush()
        event = Event(
            project_id=project.id,
            event_type="payment.approved",
            idempotency_key="payment-123",
            payload={"payment_id": "123"},
        )
        session.add(event)
        session.flush()
        message = OutboxMessage(
            aggregate_id=event.id,
            topic="webhook.event.accepted.v1",
            payload={"event_id": str(event.id)},
        )
        session.add(message)
        session.commit()

        def unavailable(_: str, __: dict[str, object]) -> None:
            raise ConnectionError("broker unavailable")

        try:
            publish_pending_messages(session, unavailable)
        except ConnectionError:
            pass
        else:
            raise AssertionError("Expected the publish error to be propagated")

        assert session.scalar(select(OutboxMessage)).status == OutboxStatus.PENDING
