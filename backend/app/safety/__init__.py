"""
app/safety package — safety gate for plan execution.

The safety gate is NOT implemented in the foundation phase.
This package defines the interface for future implementation.

The safety gate is the last checkpoint before a plan is executed.
It evaluates:
  - Whether each plan step is reversible
  - Whether the plan stays within pre-approved action boundaries
  - Whether human approval is required (e.g. for production-impacting steps)
"""

from __future__ import annotations

import abc

from app.models import Plan, WorldState


class BaseSafetyGate(abc.ABC):
    """Abstract safety gate.

    Implementations raise ``SafetyGateError`` (from ``app.core.exceptions``)
    if a plan must be blocked, or return the approved plan unchanged.
    """

    @abc.abstractmethod
    async def evaluate(self, plan: Plan, state: WorldState) -> Plan:
        """Evaluate *plan* against safety rules.

        Args:
            plan: The plan to evaluate.
            state: Current world state.

        Returns:
            The approved plan (possibly annotated).

        Raises:
            SafetyGateError: If the plan is blocked.
        """
