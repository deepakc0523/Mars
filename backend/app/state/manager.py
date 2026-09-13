"""
World-state manager for MARS.

``StateManager`` holds the authoritative ``WorldState`` for the current
incident session. It is the single source of truth consulted by the
agent loop on every INTERRUPT → RE-EVALUATE cycle.

This module contains pure deterministic state management.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.models import AgentPhase, Event, EventType, IncidentStatus, WorldState
from app.state.lifecycle import validate_lifecycle_transition

log = logging.getLogger(__name__)


def _extract_prohibitions(text: str) -> list[str]:
    """Parse human interrupt text to extract prohibited tools/actions."""
    prohibitions = []
    text_lower = text.lower()
    if "don't investigate the database" in text_lower or "don't investigate database" in text_lower:
        prohibitions.append("investigate_database")
    if "don't restart service" in text_lower or "do not restart" in text_lower:
        prohibitions.append("restart_service")
    return prohibitions


class StateManager:
    """Thread-safe holder of the current WorldState.

    Processes events deterministically and updates state snapshots.
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._state = WorldState()

    @property
    def current(self) -> WorldState:
        """Return a copy of the current world state (immutable snapshot)."""
        return self._state.model_copy()

    async def apply_event(self, event: Event) -> WorldState:
        """Apply an event to the state machine deterministically and return updated WorldState."""
        async with self._lock:
            payload = event.payload
            updates: dict[str, object] = {
                "snapshot_id": uuid4(),
                "timestamp": datetime.now(timezone.utc),
            }

            # 1. HUMAN_MESSAGE
            if event.event_type == EventType.HUMAN_MESSAGE or event.event_type == EventType.TEXT_INPUT:
                new_context = {**self._state.context, "last_human_message": payload.get("text", "")}
                updates["context"] = new_context

            # 2. HUMAN_INTERRUPT
            elif event.event_type == EventType.HUMAN_INTERRUPT:
                try:
                    new_status = validate_lifecycle_transition(
                        self._state.incident_status, IncidentStatus.INTERRUPTED
                    )
                    updates["incident_status"] = new_status
                except Exception:
                    pass  # If transition forbidden, maintain status

                updates["phase"] = AgentPhase.INTERRUPT
                text = payload.get("text", "")
                parsed_restrictions = _extract_prohibitions(text)
                given_restrictions = payload.get("restrictions", [])
                combined_restrictions = list(
                    set(self._state.restrictions + parsed_restrictions + given_restrictions)
                )
                updates["restrictions"] = combined_restrictions

                new_context = {**self._state.context}
                if "objective" in payload:
                    new_context["objective"] = payload["objective"]
                new_context["last_interrupt"] = text
                updates["context"] = new_context

            # 3. METRIC_UPDATE
            elif event.event_type == EventType.METRIC_UPDATE:
                new_metrics = {**self._state.metrics, **payload.get("metrics", {})}
                updates["metrics"] = new_metrics

            # 4. LOG_EVENT
            elif event.event_type == EventType.LOG_EVENT:
                logs = list(self._state.context.get("logs", []))
                logs.append(payload)
                updates["context"] = {**self._state.context, "logs": logs}

            # 5. DEPLOYMENT_EVENT
            elif event.event_type == EventType.DEPLOYMENT_EVENT:
                deployments = list(self._state.context.get("deployments", []))
                deployments.append(payload)
                updates["context"] = {**self._state.context, "deployments": deployments}

            # 6. RECOVERY_EVENT
            elif event.event_type == EventType.RECOVERY_EVENT:
                recoveries = list(self._state.context.get("recoveries", []))
                recoveries.append(payload)
                updates["context"] = {**self._state.context, "recoveries": recoveries}

            # 7. PLAN_CREATED
            elif event.event_type == EventType.PLAN_CREATED:
                if "plan_id" in payload:
                    updates["active_plan_id"] = UUID(str(payload["plan_id"]))
                updates["phase"] = AgentPhase.VERIFY

            # 8. PLAN_UPDATED
            elif event.event_type == EventType.PLAN_UPDATED:
                if "plan_id" in payload:
                    updates["active_plan_id"] = UUID(str(payload["plan_id"]))
                updates["phase"] = AgentPhase.REPLAN

            # 9. ACTION_STARTED
            elif event.event_type == EventType.ACTION_STARTED:
                updates["active_action"] = payload
                updates["phase"] = AgentPhase.EXECUTE

            # 10. ACTION_CANCELLED
            elif event.event_type == EventType.ACTION_CANCELLED:
                updates["active_action"] = None
                updates["phase"] = AgentPhase.REEVALUATE

            # 11. ACTION_COMPLETED
            elif event.event_type == EventType.ACTION_COMPLETED:
                updates["active_action"] = None
                completed_actions = list(self._state.context.get("completed_actions", []))
                completed_actions.append(payload)
                updates["context"] = {**self._state.context, "completed_actions": completed_actions}

            self._state = self._state.model_copy(update=updates)
            log.info("StateManager: applied event=%s -> phase=%s", event.event_type, self._state.phase)
            return self._state.model_copy()

    async def set_incident_status(self, target_status: IncidentStatus | str, *, is_reopen_event: bool = False) -> WorldState:
        """Update incident lifecycle status strictly verifying allowed transitions."""
        async with self._lock:
            valid = validate_lifecycle_transition(
                self._state.incident_status, target_status, is_reopen_event=is_reopen_event
            )
            self._state = self._state.model_copy(
                update={"incident_status": valid, "timestamp": datetime.now(timezone.utc)}
            )
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
                incident_status=IncidentStatus.DETECTED,
            )
            log.info("StateManager: state reset to idle")
            return self._state.model_copy()


# Module-level singleton.
state_manager: StateManager = StateManager()
