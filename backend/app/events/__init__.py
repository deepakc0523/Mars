"""app/events package — unified event pipeline."""

from app.events.bus import EventBus, EventHandler, event_bus
from app.events.factory import (
    make_alert_event,
    make_metric_update_event,
    make_speech_input_event,
    make_text_input_event,
)

__all__ = [
    "EventBus",
    "EventHandler",
    "event_bus",
    "make_alert_event",
    "make_metric_update_event",
    "make_speech_input_event",
    "make_text_input_event",
]
