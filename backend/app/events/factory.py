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
    """Create an event for a speech-to-text transcript.

    Note: this produces an ``Event`` with ``event_type=SPEECH_INPUT``.
    The agent loop treats TEXT_INPUT and SPEECH_INPUT identically — the
    distinction is preserved only for audit/ledger purposes.
    """
    payload: dict[str, Any] = {"text": transcript}
    if confidence is not None:
        payload["confidence"] = confidence
    return Event(
        event_type=EventType.SPEECH_INPUT,
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
