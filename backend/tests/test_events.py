"""
Tests for EventBus and event factory helpers.
"""

from __future__ import annotations

import asyncio
from uuid import UUID

import pytest

from app.events import (
    EventBus,
    make_alert_event,
    make_metric_update_event,
    make_speech_input_event,
    make_text_input_event,
)
from app.models import Event, EventType


class TestEventBus:
    def test_subscribe_and_publish(self) -> None:
        received: list[Event] = []
        bus = EventBus()

        async def handler(event: Event) -> None:
            received.append(event)

        bus.subscribe(handler)
        event = make_text_input_event("hello")
        asyncio.run(bus.publish(event))

        assert len(received) == 1
        assert received[0].event_type == EventType.TEXT_INPUT

    def test_unsubscribe_stops_delivery(self) -> None:
        received: list[Event] = []
        bus = EventBus()

        async def handler(event: Event) -> None:
            received.append(event)

        bus.subscribe(handler)
        bus.unsubscribe(handler)
        event = make_text_input_event("hello")
        asyncio.run(bus.publish(event))

        assert len(received) == 0

    def test_duplicate_subscribe_ignored(self) -> None:
        bus = EventBus()

        async def handler(event: Event) -> None:
            pass

        bus.subscribe(handler)
        bus.subscribe(handler)
        assert bus.handler_count == 1

    def test_handler_exception_does_not_propagate(self) -> None:
        bus = EventBus()

        async def bad_handler(event: Event) -> None:
            raise RuntimeError("boom")

        bus.subscribe(bad_handler)
        event = make_text_input_event("test")
        # Should not raise.
        asyncio.run(bus.publish(event))


class TestEventFactories:
    def test_text_input_event(self) -> None:
        e = make_text_input_event("hello world")
        assert e.event_type == EventType.TEXT_INPUT
        assert e.payload["text"] == "hello world"

    def test_speech_input_event(self) -> None:
        e = make_speech_input_event("voice transcript", confidence=0.95)
        assert e.event_type == EventType.SPEECH_INPUT
        assert e.payload["text"] == "voice transcript"
        assert e.payload["confidence"] == pytest.approx(0.95)

    def test_speech_and_text_same_pipeline(self) -> None:
        """Speech and text events have the same fields — same pipeline."""
        text_e = make_text_input_event("hi")
        speech_e = make_speech_input_event("hi")
        # Both are Event instances with consistent structure.
        assert isinstance(text_e, Event)
        assert isinstance(speech_e, Event)
        assert text_e.payload["text"] == speech_e.payload["text"]

    def test_alert_event(self) -> None:
        e = make_alert_event("Payment API degraded", severity="high")
        assert e.event_type == EventType.ALERT
        assert e.payload["severity"] == "high"

    def test_metric_update_event(self) -> None:
        e = make_metric_update_event({"error_rate": 0.15, "latency_p99": 2400.0})
        assert e.event_type == EventType.METRIC_UPDATE
        assert e.payload["metrics"]["error_rate"] == pytest.approx(0.15)
