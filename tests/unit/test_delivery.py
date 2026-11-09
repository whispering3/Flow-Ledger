from datetime import UTC, datetime
from unittest.mock import patch

import httpx
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from apps.api.database import Base
from apps.modules.destinations.models import Destination
from apps.modules.executions.delivery import (
    classify_response,
    deliver_execution,
    retry_after_seconds,
    retry_delay_seconds,
)
from apps.modules.executions.models import (
    AttemptOutcome,
    Execution,
    ExecutionAttempt,
    ExecutionStatus,
)
from apps.modules.organizations.models import Organization
from apps.modules.projects.models import Project
from apps.modules.webhooks.models import Event
from apps.shared.security.ssrf import SSRFBlocked, validate_public_http_destination


def create_execution(session: Session) -> Execution:
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
    destination = Destination(project_id=project.id, url="https://delivery.example/events")
    session.add_all((event, destination))
    session.flush()
    execution = Execution(project_id=project.id, event_id=event.id, destination_id=destination.id)
    session.add(execution)
    session.commit()
    return execution


def test_successful_delivery_records_immutable_attempt() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with (
        Session(engine) as session,
        patch("apps.modules.executions.delivery.validate_public_http_destination"),
    ):
        execution = create_execution(session)
        received_request: httpx.Request | None = None

        def respond(request: httpx.Request) -> httpx.Response:
            nonlocal received_request
            received_request = request
            return httpx.Response(204)

        client = httpx.Client(transport=httpx.MockTransport(respond))
        result = deliver_execution(session, execution.id, client=client, jitter=0)

        assert result.status == ExecutionStatus.SUCCEEDED
        saved = session.get(Execution, execution.id)
        attempt = session.scalar(select(ExecutionAttempt))
        assert saved.attempt_count == 1
        assert attempt.outcome == AttemptOutcome.SUCCEEDED
        assert received_request is not None
        assert received_request.headers["X-FlowLedger-Signature"].startswith("sha256=")


def test_retryable_response_is_scheduled_in_database() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    now = datetime(2026, 1, 1, tzinfo=UTC)
    with (
        Session(engine) as session,
        patch("apps.modules.executions.delivery.validate_public_http_destination"),
    ):
        execution = create_execution(session)
        client = httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(503)))
        result = deliver_execution(session, execution.id, client=client, now=now, jitter=0)

        saved = session.get(Execution, execution.id)
        assert result.status == ExecutionStatus.RETRY_SCHEDULED
        assert saved.next_attempt_at == now.replace(second=30, tzinfo=None)


def test_private_addresses_are_blocked() -> None:
    with patch("socket.getaddrinfo", return_value=[(None, None, None, None, ("127.0.0.1", 0))]):
        try:
            validate_public_http_destination("http://localhost/internal")
        except SSRFBlocked:
            pass
        else:
            raise AssertionError("Expected loopback destination to be blocked")


def test_delivery_classification_and_retry_parsing() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    assert classify_response(httpx.Response(429)) == AttemptOutcome.RETRYABLE_FAILURE
    assert classify_response(httpx.Response(400)) == AttemptOutcome.PERMANENT_FAILURE
    assert retry_delay_seconds(1) == 30
    assert retry_after_seconds("120", now) == 120
