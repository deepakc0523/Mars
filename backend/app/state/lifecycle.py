"""
Incident lifecycle state machine for MARS.

Enforces valid status transitions:
    DETECTED → INVESTIGATING → INTERRUPTED → REPLANNING → RESOLVED

Rules:
1. RESOLVED is terminal for normal status updates.
2. The ONLY valid transition out of RESOLVED is RESOLVED → DETECTED, which
   requires an explicit new-trigger/reopen event.
"""

from app.core.exceptions import MARSError
from app.models import IncidentStatus


class InvalidLifecycleTransitionError(MARSError):
    """Raised when an invalid incident status transition is attempted."""

    def __init__(self, current: IncidentStatus, target: IncidentStatus, reason: str = ""):
        message = (
            f"Invalid incident lifecycle transition: '{current.value}' → '{target.value}'."
        )
        if reason:
            message += f" {reason}"
        super().__init__(message)
        self.current = current
        self.target = target


VALID_TRANSITIONS: dict[IncidentStatus, set[IncidentStatus]] = {
    IncidentStatus.DETECTED: {IncidentStatus.INVESTIGATING, IncidentStatus.RESOLVED},
    IncidentStatus.INVESTIGATING: {
        IncidentStatus.INTERRUPTED,
        IncidentStatus.REPLANNING,
        IncidentStatus.RESOLVED,
    },
    IncidentStatus.INTERRUPTED: {IncidentStatus.REPLANNING, IncidentStatus.RESOLVED},
    IncidentStatus.REPLANNING: {
        IncidentStatus.INVESTIGATING,
        IncidentStatus.INTERRUPTED,
        IncidentStatus.RESOLVED,
    },
    IncidentStatus.RESOLVED: set(),  # Terminal for normal updates
}


def validate_lifecycle_transition(
    current: IncidentStatus | str,
    target: IncidentStatus | str,
    *,
    is_reopen_event: bool = False,
) -> IncidentStatus:
    """
    Validate and return target status if the transition is allowed.

    Raises InvalidLifecycleTransitionError if forbidden.
    """
    if isinstance(current, str):
        current = IncidentStatus(current)
    if isinstance(target, str):
        target = IncidentStatus(target)

    if current == target:
        return target

    # Handle RESOLVED terminal status check
    if current == IncidentStatus.RESOLVED:
        if target == IncidentStatus.DETECTED and is_reopen_event:
            return target
        raise InvalidLifecycleTransitionError(
            current,
            target,
            reason="RESOLVED is a terminal state. Only a new-trigger event (RESOLVED → DETECTED) can reopen an incident.",
        )

    allowed = VALID_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise InvalidLifecycleTransitionError(current, target)

    return target
