"""
World-state manager for MARS.

``StateManager`` holds the authoritative ``WorldState`` for the current
incident session. It is the single source of truth consulted by the
agent loop on every INTERRUPT → RE-EVALUATE cycle.

This module contains no AI logic. It is pure state management.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.models import AgentPhase, WorldState

log = logging.getLogger(__name__)


class StateManager:
    """Thread-safe (asyncio-safe) holder of the current WorldState.

    All mutations go through explicit methods so we have a single place
    to add persistence, snapshots, or event emission later.
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._state = WorldState()

    @property
    def current(self) -> WorldState:
        """Return a copy of the current world state (immutable snapshot)."""
        return self._state.model_copy()

    async def transition_phase(self, phase: AgentPhase) -> WorldState:
        """Atomically update the agent phase and return the new state."""
        async with self._lock:
            self._state = self._state.model_copy(
                update={
                    "phase": phase,
                    "timestamp": datetime.now(timezone.utc),
                }
            )
            log.info("StateManager: phase → %s", phase.value)
            return self._state.model_copy()

    async def update_metrics(self, metrics: dict[str, float]) -> WorldState:
        """Merge *metrics* into the current state and return the new state."""
        async with self._lock:
            merged = {**self._state.metrics, **metrics}
            self._state = self._state.model_copy(
                update={
                    "metrics": merged,
                    "timestamp": datetime.now(timezone.utc),
                }
            )
            log.debug("StateManager: metrics updated keys=%s", list(metrics.keys()))
            return self._state.model_copy()

    async def set_active_plan(self, plan_id: UUID | None) -> WorldState:
        """Record which plan is currently being executed."""
        async with self._lock:
            self._state = self._state.model_copy(
                update={
                    "active_plan_id": plan_id,
                    "timestamp": datetime.now(timezone.utc),
                }
            )
            log.info("StateManager: active_plan_id → %s", plan_id)
            return self._state.model_copy()

    async def set_incident(self, incident_id: UUID | None) -> WorldState:
        """Associate the state manager with an incident."""
        async with self._lock:
            self._state = self._state.model_copy(
                update={
                    "incident_id": incident_id,
                    "timestamp": datetime.now(timezone.utc),
                }
            )
            log.info("StateManager: incident_id → %s", incident_id)
            return self._state.model_copy()

    async def update_context(self, **kwargs: object) -> WorldState:
        """Merge arbitrary key-value pairs into the context dict."""
        async with self._lock:
            merged = {**self._state.context, **kwargs}
            self._state = self._state.model_copy(
                update={
                    "context": merged,
                    "timestamp": datetime.now(timezone.utc),
                }
            )
            return self._state.model_copy()

    async def reset(self) -> WorldState:
        """Reset to a clean idle state (e.g. after incident resolution)."""
        async with self._lock:
            self._state = WorldState(
                snapshot_id=uuid4(),
                phase=AgentPhase.IDLE,
            )
            log.info("StateManager: state reset to idle")
            return self._state.model_copy()


# Module-level singleton.
state_manager: StateManager = StateManager()
