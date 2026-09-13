"""
Event factory helpers for MARS.

Centralise event construction so the rest of the codebase never builds
``Event`` dicts by hand.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.models import Event, EventType


def make_text_input_event(
    text: str,
    *,
    source: str = "user",
    correlation_id: UUID | None = None,
) -> Event:
    """Create an event for a human text message."""
    return Event(
        event_type=EventType.TEXT_INPUT,
        source=source,
        payload={"text": text},
        correlation_id=correlation_id,
    )


def make_speech_input_event(
    transcript: str,
    *,
    confidence: float | None = None,
    source: str = "user",
    correlation_id: UUID | None = None,
) -> Event:
    """Create an event for a speech-to-text transcript."""
    payload: dict[str, Any] = {"text": transcript}
    if confidence is not None:
        payload["confidence"] = confidence
    return Event(
        event_type=EventType.SPEECH_INPUT,
        source=source,
        payload=payload,
        correlation_id=correlation_id,
    )


def make_human_message_event(
    text: str,
    *,
    source: str = "user",
    correlation_id: UUID | None = None,
    **extra: Any,
) -> Event:
    """Create a human operational message event."""
    return Event(
        event_type=EventType.HUMAN_MESSAGE,
        source=source,
        payload={"text": text, **extra},
        correlation_id=correlation_id,
    )


def make_human_interrupt_event(
    text: str,
    *,
    restrictions: list[str] | None = None,
    objective: str | None = None,
    source: str = "user",
    correlation_id: UUID | None = None,
) -> Event:
    """Create a human interrupt event carrying explicit constraints or commands."""
    payload: dict[str, Any] = {"text": text}
    if restrictions is not None:
        payload["restrictions"] = restrictions
    if objective is not None:
        payload["objective"] = objective
    return Event(
        event_type=EventType.HUMAN_INTERRUPT,
        source=source,
        payload=payload,
        correlation_id=correlation_id,
    )


def make_alert_event(
    message: str,
    severity: str = "medium",
    *,
    source: str = "system",
    correlation_id: UUID | None = None,
    **extra: Any,
) -> Event:
    """Create a system alert event."""
    return Event(
        event_type=EventType.ALERT,
        source=source,
        payload={"message": message, "severity": severity, **extra},
        correlation_id=correlation_id,
    )


def make_metric_update_event(
    metrics: dict[str, float],
    *,
    source: str = "monitoring",
    correlation_id: UUID | None = None,
) -> Event:
    """Create a metric-update event carrying a snapshot of current metrics."""
    return Event(
        event_type=EventType.METRIC_UPDATE,
        source=source,
        payload={"metrics": metrics},
        correlation_id=correlation_id,
    )


def make_log_event(
    message: str,
    level: str = "info",
    *,
    source: str = "system",
    correlation_id: UUID | None = None,
    **extra: Any,
) -> Event:
    """Create a log record event."""
    return Event(
        event_type=EventType.LOG_EVENT,
        source=source,
        payload={"message": message, "level": level, **extra},
        correlation_id=correlation_id,
    )


def make_deployment_event(
    service: str,
    version: str,
    status: str = "deployed",
    *,
    source: str = "cicd",
    correlation_id: UUID | None = None,
    **extra: Any,
) -> Event:
    """Create a deployment notification event."""
    return Event(
        event_type=EventType.DEPLOYMENT_EVENT,
        source=source,
        payload={"service": service, "version": version, "status": status, **extra},
        correlation_id=correlation_id,
    )


def make_recovery_event(
    service: str,
    status: str = "recovered",
    *,
    source: str = "monitoring",
    correlation_id: UUID | None = None,
    **extra: Any,
) -> Event:
    """Create a service recovery notification event."""
    return Event(
        event_type=EventType.RECOVERY_EVENT,
        source=source,
        payload={"service": service, "status": status, **extra},
        correlation_id=correlation_id,
    )


def make_plan_created_event(
    plan_id: UUID | str,
    incident_id: UUID | str,
    steps: list[dict[str, Any]],
    rationale: str = "",
    *,
    source: str = "planner",
    correlation_id: UUID | None = None,
) -> Event:
    """Create a plan-created event."""
    return Event(
        event_type=EventType.PLAN_CREATED,
        source=source,
        payload={
            "plan_id": str(plan_id),
            "incident_id": str(incident_id),
            "steps": steps,
            "rationale": rationale,
        },
        correlation_id=correlation_id,
    )


def make_plan_updated_event(
    plan_id: UUID | str,
    incident_id: UUID | str,
    steps: list[dict[str, Any]],
    rationale: str = "",
    *,
    source: str = "planner",
    correlation_id: UUID | None = None,
) -> Event:
    """Create a plan-updated event."""
    return Event(
        event_type=EventType.PLAN_UPDATED,
        source=source,
        payload={
            "plan_id": str(plan_id),
            "incident_id": str(incident_id),
            "steps": steps,
            "rationale": rationale,
        },
        correlation_id=correlation_id,
    )


def make_action_started_event(
    action_id: UUID | str,
    tool_name: str,
    input_payload: dict[str, Any],
    *,
    plan_id: UUID | str | None = None,
    step_id: UUID | str | None = None,
    source: str = "executor",
    correlation_id: UUID | None = None,
) -> Event:
    """Create an action-started event."""
    return Event(
        event_type=EventType.ACTION_STARTED,
        source=source,
        payload={
            "action_id": str(action_id),
            "tool_name": tool_name,
            "input_payload": input_payload,
            "plan_id": str(plan_id) if plan_id else None,
            "step_id": str(step_id) if step_id else None,
        },
        correlation_id=correlation_id,
    )


def make_action_cancelled_event(
    action_id: UUID | str,
    tool_name: str,
    reason: str = "",
    *,
    plan_id: UUID | str | None = None,
    step_id: UUID | str | None = None,
    source: str = "executor",
    correlation_id: UUID | None = None,
) -> Event:
    """Create an action-cancelled event."""
    return Event(
        event_type=EventType.ACTION_CANCELLED,
        source=source,
        payload={
            "action_id": str(action_id),
            "tool_name": tool_name,
            "reason": reason,
            "plan_id": str(plan_id) if plan_id else None,
            "step_id": str(step_id) if step_id else None,
        },
        correlation_id=correlation_id,
    )


def make_action_completed_event(
    action_id: UUID | str,
    tool_name: str,
    output_payload: dict[str, Any],
    *,
    plan_id: UUID | str | None = None,
    step_id: UUID | str | None = None,
    source: str = "executor",
    correlation_id: UUID | None = None,
) -> Event:
    """Create an action-completed event."""
    return Event(
        event_type=EventType.ACTION_COMPLETED,
        source=source,
        payload={
            "action_id": str(action_id),
            "tool_name": tool_name,
            "output_payload": output_payload,
            "plan_id": str(plan_id) if plan_id else None,
            "step_id": str(step_id) if step_id else None,
        },
        correlation_id=correlation_id,
    )


def make_action_failed_event(
    action_id: UUID | str,
    tool_name: str,
    error_message: str,
    *,
    plan_id: UUID | str | None = None,
    step_id: UUID | str | None = None,
    source: str = "executor",
    correlation_id: UUID | None = None,
) -> Event:
    """Create an action-failed event."""
    return Event(
        event_type=EventType.ACTION_FAILED,
        source=source,
        payload={
            "action_id": str(action_id),
            "tool_name": tool_name,
            "error_message": error_message,
            "plan_id": str(plan_id) if plan_id else None,
            "step_id": str(step_id) if step_id else None,
        },
        correlation_id=correlation_id,
    )
