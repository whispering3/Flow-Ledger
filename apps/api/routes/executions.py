from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from apps.api.dependencies import DbSession, ProjectDependency
from apps.modules.executions.delivery import retry_dead_letter
from apps.modules.executions.models import Execution, ExecutionAttempt, ExecutionStatus

router = APIRouter(prefix="/executions", tags=["executions"])


class AttemptOutput(BaseModel):
    id: UUID
    attempt_number: int
    outcome: str
    response_code: int | None
    error_code: str | None
    duration_ms: int | None

    model_config = {"from_attributes": True}


class ExecutionOutput(BaseModel):
    id: UUID
    delivery_id: UUID
    event_id: UUID
    destination_id: UUID
    status: ExecutionStatus
    attempt_count: int

    model_config = {"from_attributes": True}


class ExecutionDetail(ExecutionOutput):
    attempts: list[AttemptOutput]


@router.get("", response_model=list[ExecutionOutput])
def list_executions(
    db: DbSession,
    project: ProjectDependency,
    execution_status: ExecutionStatus | None = None,
) -> list[Execution]:
    statement = select(Execution).where(Execution.project_id == project.id)
    if execution_status is not None:
        statement = statement.where(Execution.status == execution_status)
    return list(db.scalars(statement.order_by(Execution.created_at.desc())))


@router.get("/{execution_id}", response_model=ExecutionDetail)
def get_execution(execution_id: UUID, db: DbSession, project: ProjectDependency) -> ExecutionDetail:
    execution = db.scalar(
        select(Execution).where(
            Execution.id == execution_id,
            Execution.project_id == project.id,
        )
    )
    if execution is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")
    attempts = list(
        db.scalars(
            select(ExecutionAttempt)
            .where(ExecutionAttempt.execution_id == execution.id)
            .order_by(ExecutionAttempt.attempt_number)
        )
    )
    return ExecutionDetail(
        id=execution.id,
        delivery_id=execution.delivery_id,
        event_id=execution.event_id,
        destination_id=execution.destination_id,
        status=execution.status,
        attempt_count=execution.attempt_count,
        attempts=[AttemptOutput.model_validate(attempt) for attempt in attempts],
    )


@router.post("/{execution_id}/retry", response_model=ExecutionOutput)
def retry_execution(execution_id: UUID, db: DbSession, project: ProjectDependency) -> Execution:
    execution = db.scalar(
        select(Execution).where(
            Execution.id == execution_id,
            Execution.project_id == project.id,
        )
    )
    if execution is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")
    try:
        return retry_dead_letter(db, execution_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
