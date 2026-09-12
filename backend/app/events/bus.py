"""
Event bus for MARS.

``EventBus`` is an in-process asyncio pub/sub bus. Every component that
wants to react to events (agent loop, WebSocket broadcaster, logger)
subscribes via ``subscribe()``. Every component that emits events calls
``publish()``.

This is the ONLY place events are dispatched — there is deliberately no
separate path for speech vs text inputs.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Coroutine
from typing import Any

from app.models import Event

log = logging.getLogger(__name__)

# Type alias for an async event handler.
EventHandler = Callable[[Event], Coroutine[Any, Any, None]]


class EventBus:
    """Async publish-subscribe event bus.

    Usage::

        bus = EventBus()

        async def my_handler(event: Event) -> None:
            print(event)

        bus.subscribe(my_handler)
        await bus.publish(some_event)
    """

    def __init__(self) -> None:
        self._handlers: list[EventHandler] = []

    def subscribe(self, handler: EventHandler) -> None:
        """Register an async handler to receive all published events."""
        if handler not in self._handlers:
            self._handlers.append(handler)
            log.debug("EventBus: subscribed handler %s", handler.__qualname__)

    def unsubscribe(self, handler: EventHandler) -> None:
        """Remove a previously registered handler."""
        try:
            self._handlers.remove(handler)
            log.debug("EventBus: unsubscribed handler %s", handler.__qualname__)
        except ValueError:
            pass  # Not registered — silently ignore.

    async def publish(self, event: Event) -> None:
        """Dispatch *event* to all registered handlers concurrently.

        Exceptions raised by individual handlers are logged but do not
        prevent other handlers from running.
        """
        log.debug(
            "EventBus: publishing event_type=%s id=%s", event.event_type, event.id
        )
        if not self._handlers:
            return

        results = await asyncio.gather(
            *[handler(event) for handler in self._handlers],
            return_exceptions=True,
        )

        for handler, result in zip(self._handlers, results):
            if isinstance(result, Exception):
                log.error(
                    "EventBus: handler %s raised %s: %s",
                    handler.__qualname__,
                    type(result).__name__,
                    result,
                )

    @property
    def handler_count(self) -> int:
        """Number of currently registered handlers."""
        return len(self._handlers)


# Module-level singleton — import and use directly.
event_bus: EventBus = EventBus()
