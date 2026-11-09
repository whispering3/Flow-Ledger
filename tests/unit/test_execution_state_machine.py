import pytest

from apps.modules.executions.models import ExecutionStatus
from apps.modules.executions.state_machine import require_transition, transition_is_allowed


def test_execution_state_machine_allows_delivery_lifecycle() -> None:
    assert transition_is_allowed(ExecutionStatus.PENDING, ExecutionStatus.IN_PROGRESS)
    assert transition_is_allowed(ExecutionStatus.IN_PROGRESS, ExecutionStatus.RETRY_SCHEDULED)
    assert transition_is_allowed(ExecutionStatus.RETRY_SCHEDULED, ExecutionStatus.IN_PROGRESS)
    assert transition_is_allowed(ExecutionStatus.IN_PROGRESS, ExecutionStatus.SUCCEEDED)


def test_execution_state_machine_rejects_terminal_transition() -> None:
    with pytest.raises(ValueError, match="Invalid execution transition"):
        require_transition(ExecutionStatus.SUCCEEDED, ExecutionStatus.PENDING)
