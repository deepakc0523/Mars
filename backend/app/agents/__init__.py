"""
app/agents package — AI agent implementations.

Agents are NOT implemented in the foundation phase.
This package defines the interface that all agents must satisfy.
"""

from __future__ import annotations

import abc

from app.models import Event, Plan, WorldState


class BaseAgent(abc.ABC):
    """Abstract base class for all MARS agents.

    Every agent — planner, verifier, or future specialist — implements
    this interface. The agent loop calls ``handle_event`` for every event
    that the agent is subscribed to, and ``generate_plan`` when a new plan
    is required.
    """

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Human-readable agent name (e.g. 'PlannerAgent')."""

    @abc.abstractmethod
    async def handle_event(self, event: Event) -> None:
        """React to an event from the event bus.

        Args:
            event: The event to process.
        """

    @abc.abstractmethod
    async def generate_plan(self, state: WorldState) -> Plan:
        """Produce a new plan given the current world state.

        Args:
            state: A snapshot of the current world state.

        Returns:
            A ``Plan`` with status ``PENDING``.
        """
