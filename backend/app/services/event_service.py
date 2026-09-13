"""
Event processing service orchestrating verification, publishing, state updates, DB persistence, and WebSocket broadcasts.
"""

from __future__ import annotations

import logging
from sqlalchemy.orm import Session

from app.db.models.event import EventModel
from app.db.models.world_state import WorldStateSnapshotModel
from app.events.bus import event_bus
from app.models import Event, WorldState
from app.repositories import EventRepository, WorldStateRepository, IncidentRepository
from app.state.manager import state_manager
from app.ws.manager import ws_manager

log = logging.getLogger(__name__)


class EventService:
    """Service handling the end-to-end event processing flow."""

    async def process_event(self, event: Event, db: Session) -> tuple[Event, WorldState]:
        """
        Process an incoming event through the complete MARS pipeline:
          1. Publish to EventBus subscribers
          2. Apply deterministic state transition in StateManager
          3. Persist Event to SQLite
          4. Persist resulting WorldState snapshot to SQLite
          5. Update incident status if applicable
          6. Broadcast event and state update to WebSocket clients
        """
        log.info("EventService: processing event id=%s type=%s", event.id, event.event_type)

        # 1. Publish to in-memory bus
        await event_bus.publish(event)

        # 2. State transition
        updated_state = await state_manager.apply_event(event)

        # 3. Persist Event to SQLite
        event_repo = EventRepository(db)
        event_repo.create(
            EventModel(
                id=str(event.id),
                event_type=event.event_type.value,
                source=event.source,
                payload_json=event.payload,
                correlation_id=str(event.correlation_id) if event.correlation_id else None,
                timestamp=event.timestamp,
            )
        )

        # 4. Persist WorldState snapshot to SQLite
        ws_repo = WorldStateRepository(db)
        ws_repo.create(
            WorldStateSnapshotModel(
                id=str(updated_state.snapshot_id),
                incident_id=str(updated_state.incident_id) if updated_state.incident_id else None,
                phase=updated_state.phase.value,
                active_plan_id=str(updated_state.active_plan_id) if updated_state.active_plan_id else None,
                metrics_json=updated_state.metrics,
                context_json={
                    **updated_state.context,
                    "restrictions": updated_state.restrictions,
                    "incident_status": updated_state.incident_status.value,
                },
                timestamp=updated_state.timestamp,
            )
        )

        # 5. Sync incident status if present
        if updated_state.incident_id:
            inc_repo = IncidentRepository(db)
            inc = inc_repo.get_by_id(str(updated_state.incident_id))
            if inc and inc.status != updated_state.incident_status.value:
                inc.status = updated_state.incident_status.value
                db.commit()

        # 6. Broadcast via WebSocket
        broadcast_payload = {
            "type": "event_processed",
            "event": event.model_dump(mode="json"),
            "state": updated_state.model_dump(mode="json"),
        }
        await ws_manager.broadcast(broadcast_payload)

        return event, updated_state
