from app.domain.models import RunStatus

ALLOWED_TRANSITIONS: dict[RunStatus, frozenset[RunStatus]] = {
    RunStatus.CREATED: frozenset({RunStatus.RUNNING, RunStatus.FAILED}),
    RunStatus.RUNNING: frozenset(
        {RunStatus.WAITING_FOR_APPROVAL, RunStatus.COMPLETE, RunStatus.FAILED}
    ),
    RunStatus.WAITING_FOR_APPROVAL: frozenset(
        {RunStatus.RUNNING, RunStatus.COMPLETE, RunStatus.FAILED}
    ),
    RunStatus.COMPLETE: frozenset(),
    RunStatus.FAILED: frozenset(),
}


class InvalidStateTransition(ValueError):
    pass


def validate_transition(current: RunStatus, target: RunStatus) -> None:
    if target not in ALLOWED_TRANSITIONS[current]:
        raise InvalidStateTransition(f"Cannot transition run from {current} to {target}")
