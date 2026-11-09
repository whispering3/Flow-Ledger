from apps.modules.executions.models import ExecutionStatus

_ALLOWED_TRANSITIONS: dict[ExecutionStatus, set[ExecutionStatus]] = {
    ExecutionStatus.PENDING: {ExecutionStatus.IN_PROGRESS},
    ExecutionStatus.IN_PROGRESS: {
        ExecutionStatus.SUCCEEDED,
        ExecutionStatus.RETRY_SCHEDULED,
        ExecutionStatus.DEAD_LETTERED,
    },
    ExecutionStatus.RETRY_SCHEDULED: {ExecutionStatus.IN_PROGRESS},
    ExecutionStatus.SUCCEEDED: set(),
    ExecutionStatus.DEAD_LETTERED: {ExecutionStatus.PENDING},
}


def transition_is_allowed(current: ExecutionStatus, target: ExecutionStatus) -> bool:
    return target in _ALLOWED_TRANSITIONS[current]


def require_transition(current: ExecutionStatus, target: ExecutionStatus) -> None:
    if not transition_is_allowed(current, target):
        raise ValueError(f"Invalid execution transition: {current} -> {target}")
