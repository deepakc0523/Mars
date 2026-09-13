"""
API router for event ingestion and event history lookup.
"""

from typing import Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models import Event, EventType
from app.repositories import EventRepository
from app.services import EventService

router = APIRouter(prefix="/events", tags=["events"])


@router.post("", response_model=dict[str, Any], status_code=201)
async def post_event(event: Event, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Ingest, process, and persist an operational event."""
    svc = EventService()
    processed_evt, state = await svc.process_event(event, db)
    return {
        "status": "processed",
        "event": processed_evt.model_dump(mode="json"),
        "state": state.model_dump(mode="json"),
    }


@router.get("/history", response_model=list[dict[str, Any]])
def get_event_history(
    event_type: EventType | None = Query(None, description="Filter by event type"),
    correlation_id: str | None = Query(None, description="Filter by correlation ID"),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """Retrieve historical events stored in SQLite."""
    repo = EventRepository(db)
    if correlation_id:
        events = repo.get_by_correlation_id(correlation_id)
    else:
        events = repo.list_recent_events(
            event_type=event_type.value if event_type else None, limit=limit
        )

    return [
        {
            "id": e.id,
            "event_type": e.event_type,
            "source": e.source,
            "payload": e.payload_json,
            "correlation_id": e.correlation_id,
            "timestamp": e.timestamp.isoformat(),
        }
        for e in events
    ]
