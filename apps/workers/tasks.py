from datetime import UTC, datetime
from uuid import UUID

from apps.api.database import SessionLocal
from apps.modules.executions.delivery import (
    deliver_execution,
    due_execution_ids,
    recover_stale_executions,
)
from apps.modules.executions.service import materialize_executions
from apps.modules.webhooks.outbox import publish_pending_messages
from apps.workers.celery_app import celery_app


@celery_app.task(name="flowledger.outbox.publish_pending")
def publish_pending_outbox() -> int:
    with SessionLocal() as session:
        return publish_pending_messages(
            session,
            lambda topic, payload: celery_app.send_task(topic, kwargs=payload),
        )


@celery_app.task(name="webhook.event.accepted.v1")
def materialize_event_executions(event_id: str, **_: str) -> int:
    with SessionLocal() as session:
        return len(materialize_executions(session, UUID(event_id)))


@celery_app.task(name="flowledger.executions.dispatch_due")
def dispatch_due_executions() -> int:
    with SessionLocal() as session:
        execution_ids = due_execution_ids(session, datetime.now(UTC))
    for execution_id in execution_ids:
        celery_app.send_task(
            "flowledger.executions.deliver", kwargs={"execution_id": str(execution_id)}
        )
    return len(execution_ids)


@celery_app.task(name="flowledger.executions.deliver")
def deliver_outbound_execution(execution_id: str) -> str:
    with SessionLocal() as session:
        return deliver_execution(session, UUID(execution_id)).status


@celery_app.task(name="flowledger.executions.recover_stale")
def recover_stale_delivery_executions() -> int:
    with SessionLocal() as session:
        return recover_stale_executions(session, datetime.now(UTC))
