from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from apps.api.database import Base
from apps.modules.destinations.models import Destination
from apps.modules.executions.models import Execution
from apps.modules.executions.service import materialize_executions
from apps.modules.organizations.models import Organization
from apps.modules.projects.models import Project
from apps.modules.webhooks.models import Event


def test_execution_materialization_is_filtered_and_idempotent() -> None:
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
        matching = Destination(project_id=project.id, url="https://example.com/all", event_types=[])
        filtered = Destination(
            project_id=project.id,
            url="https://example.com/payments",
            event_types=["payment.approved"],
        )
        ignored = Destination(
            project_id=project.id,
            url="https://example.com/orders",
            event_types=["order.created"],
        )
        session.add_all((event, matching, filtered, ignored))
        session.commit()

        created = materialize_executions(session, event.id)
        duplicated = materialize_executions(session, event.id)

        assert len(created) == 2
        assert duplicated == []
        assert len(session.scalars(select(Execution)).all()) == 2
