import hashlib
import hmac
import json
import math
import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from typing import Protocol
from uuid import UUID

import httpx
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from apps.modules.destinations.models import Destination
from apps.modules.executions.models import (
    AttemptOutcome,
    Execution,
    ExecutionAttempt,
    ExecutionStatus,
)
from apps.modules.executions.state_machine import require_transition
from apps.modules.webhooks.models import Event
from apps.shared.security.secrets import decrypt_secret
from apps.shared.security.ssrf import SSRFBlocked, validate_public_http_destination

MAX_ATTEMPTS = 8
CONNECT_TIMEOUT_SECONDS = 3.0
REQUEST_TIMEOUT_SECONDS = 10.0
STALE_EXECUTION_SECONDS = 15 * 60


@dataclass(frozen=True)
class DeliveryResult:
    execution_id: UUID
    status: ExecutionStatus
    attempted: bool


class SupportsPost(Protocol):
    def post(self, url: str, **kwargs: object) -> httpx.Response: ...


def retry_delay_seconds(attempt_number: int, jitter: float = 0.0) -> int:
    if attempt_number < 1:
        raise ValueError("attempt_number must be positive")
    base = min(30 * (2 ** (attempt_number - 1)), 3600)
    return math.ceil(base + min(max(jitter, 0.0), base * 0.2))


def classify_response(response: httpx.Response) -> AttemptOutcome:
    if 200 <= response.status_code < 300:
        return AttemptOutcome.SUCCEEDED
    if response.status_code == 429 or response.status_code >= 500:
        return AttemptOutcome.RETRYABLE_FAILURE
    return AttemptOutcome.PERMANENT_FAILURE


def retry_after_seconds(value: str | None, now: datetime) -> int | None:
    if not value:
        return None
    try:
        return min(max(int(value), 0), 3600)
    except ValueError:
        try:
            retry_at = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None
        if retry_at.tzinfo is None:
            retry_at = retry_at.replace(tzinfo=UTC)
        return min(max(math.ceil((retry_at - now).total_seconds()), 0), 3600)


def _claim_execution(session: Session, execution_id: UUID, now: datetime) -> Execution | None:
    execution = session.scalar(
        select(Execution).where(Execution.id == execution_id).with_for_update()
    )
    if execution is None:
        raise LookupError(f"Execution {execution_id} does not exist")
    if execution.status not in {ExecutionStatus.PENDING, ExecutionStatus.RETRY_SCHEDULED}:
        return None
    if execution.next_attempt_at is not None and execution.next_attempt_at > now:
        return None
    require_transition(execution.status, ExecutionStatus.IN_PROGRESS)
    execution.status = ExecutionStatus.IN_PROGRESS
    execution.started_at = now
    session.commit()
    return execution


def deliver_execution(
    session: Session,
    execution_id: UUID,
    *,
    client: SupportsPost | None = None,
    now: datetime | None = None,
    jitter: float | None = None,
) -> DeliveryResult:
    now = now or datetime.now(UTC)
    execution = _claim_execution(session, execution_id, now)
    if execution is None:
        current = session.get(Execution, execution_id)
        if current is None:
            raise LookupError(f"Execution {execution_id} does not exist")
        return DeliveryResult(execution_id=execution_id, status=current.status, attempted=False)

    destination = session.get(Destination, execution.destination_id)
    event = session.get(Event, execution.event_id)
    if destination is None or event is None:
        raise RuntimeError("Execution references missing delivery data")

    started_monotonic = datetime.now(UTC)
    response: httpx.Response | None = None
    error_code: str | None = None
    retry_after: int | None = None
    try:
        validate_public_http_destination(destination.url)
        payload_bytes = json.dumps(event.payload, separators=(",", ":"), ensure_ascii=False).encode(
            "utf-8"
        )
        signature = hmac.new(
            decrypt_secret(destination.signing_secret_ciphertext).encode("utf-8"),
            payload_bytes,
            hashlib.sha256,
        ).hexdigest()
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "FlowLedger/0.1",
            "X-FlowLedger-Event-Id": str(event.id),
            "X-FlowLedger-Delivery-Id": str(execution.delivery_id),
            "X-FlowLedger-Event-Type": event.event_type,
            "X-FlowLedger-Attempt": str(execution.attempt_count + 1),
            "X-FlowLedger-Signature": f"sha256={signature}",
        }
        if client is None:
            with httpx.Client(
                follow_redirects=False,
                trust_env=False,
                timeout=httpx.Timeout(REQUEST_TIMEOUT_SECONDS, connect=CONNECT_TIMEOUT_SECONDS),
            ) as managed_client:
                response = managed_client.post(
                    destination.url, content=payload_bytes, headers=headers
                )
        else:
            response = client.post(destination.url, content=payload_bytes, headers=headers)
        outcome = classify_response(response)
        retry_after = retry_after_seconds(response.headers.get("Retry-After"), now)
    except SSRFBlocked:
        outcome = AttemptOutcome.PERMANENT_FAILURE
        error_code = "ssrf_blocked"
    except httpx.TimeoutException:
        outcome = AttemptOutcome.RETRYABLE_FAILURE
        error_code = "timeout"
    except httpx.HTTPError:
        outcome = AttemptOutcome.RETRYABLE_FAILURE
        error_code = "network_error"

    finished_at = datetime.now(UTC)
    duration_ms = max(0, round((finished_at - started_monotonic).total_seconds() * 1000))
    return _record_outcome(
        session,
        execution_id=execution_id,
        outcome=outcome,
        response_code=response.status_code if response is not None else None,
        error_code=error_code,
        duration_ms=duration_ms,
        now=now,
        retry_after=retry_after,
        jitter=random.uniform(0, 6) if jitter is None else jitter,
    )


def _record_outcome(
    session: Session,
    *,
    execution_id: UUID,
    outcome: AttemptOutcome,
    response_code: int | None,
    error_code: str | None,
    duration_ms: int,
    now: datetime,
    retry_after: int | None,
    jitter: float,
) -> DeliveryResult:
    execution = session.scalar(
        select(Execution).where(Execution.id == execution_id).with_for_update()
    )
    if execution is None:
        raise LookupError(f"Execution {execution_id} does not exist")
    attempt_number = execution.attempt_count + 1
    session.add(
        ExecutionAttempt(
            execution_id=execution.id,
            attempt_number=attempt_number,
            outcome=outcome,
            response_code=response_code,
            error_code=error_code,
            duration_ms=duration_ms,
        )
    )
    execution.attempt_count = attempt_number
    execution.started_at = None
    if outcome is AttemptOutcome.SUCCEEDED:
        require_transition(execution.status, ExecutionStatus.SUCCEEDED)
        execution.status = ExecutionStatus.SUCCEEDED
        execution.completed_at = now
        execution.next_attempt_at = None
    elif outcome is AttemptOutcome.RETRYABLE_FAILURE and attempt_number < MAX_ATTEMPTS:
        require_transition(execution.status, ExecutionStatus.RETRY_SCHEDULED)
        execution.status = ExecutionStatus.RETRY_SCHEDULED
        delay = (
            retry_after if retry_after is not None else retry_delay_seconds(attempt_number, jitter)
        )
        execution.next_attempt_at = now + timedelta(seconds=delay)
    else:
        require_transition(execution.status, ExecutionStatus.DEAD_LETTERED)
        execution.status = ExecutionStatus.DEAD_LETTERED
        execution.completed_at = now
        execution.next_attempt_at = None
    session.commit()
    return DeliveryResult(execution_id=execution.id, status=execution.status, attempted=True)


def due_execution_ids(session: Session, now: datetime, limit: int = 100) -> list[UUID]:
    return list(
        session.scalars(
            select(Execution.id)
            .where(
                or_(
                    Execution.status == ExecutionStatus.PENDING,
                    (
                        Execution.status == ExecutionStatus.RETRY_SCHEDULED,
                        Execution.next_attempt_at <= now,
                    ),
                )
            )
            .order_by(Execution.created_at)
            .limit(limit)
        )
    )


def recover_stale_executions(session: Session, now: datetime) -> int:
    stale_before = now - timedelta(seconds=STALE_EXECUTION_SECONDS)
    executions = session.scalars(
        select(Execution)
        .where(
            Execution.status == ExecutionStatus.IN_PROGRESS,
            Execution.started_at <= stale_before,
        )
        .with_for_update(skip_locked=True)
    ).all()
    for execution in executions:
        require_transition(execution.status, ExecutionStatus.RETRY_SCHEDULED)
        execution.status = ExecutionStatus.RETRY_SCHEDULED
        execution.next_attempt_at = now
        execution.started_at = None
    session.commit()
    return len(executions)


def retry_dead_letter(
    session: Session, execution_id: UUID, now: datetime | None = None
) -> Execution:
    execution = session.scalar(
        select(Execution).where(Execution.id == execution_id).with_for_update()
    )
    if execution is None:
        raise LookupError(f"Execution {execution_id} does not exist")
    if execution.status != ExecutionStatus.DEAD_LETTERED:
        raise ValueError("Only dead-lettered executions can be retried manually")
    require_transition(execution.status, ExecutionStatus.PENDING)
    execution.status = ExecutionStatus.PENDING
    execution.next_attempt_at = now or datetime.now(UTC)
    execution.completed_at = None
    session.commit()
    session.refresh(execution)
    return execution
