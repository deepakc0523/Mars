"""
Repository for event log persistence and queries.
"""

from typing import Sequence
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.event import EventModel
from app.repositories.base import BaseRepository


class EventRepository(BaseRepository[EventModel]):
    """Repository managing operational event records."""

    def __init__(self, db: Session) -> None:
        super().__init__(EventModel, db)

    def get_by_correlation_id(self, correlation_id: str) -> Sequence[EventModel]:
        """Fetch all events linked to a correlation ID."""
        stmt = (
            select(EventModel)
            .where(EventModel.correlation_id == correlation_id)
            .order_by(EventModel.timestamp.asc())
        )
        return self.db.scalars(stmt).all()

    def list_recent_events(
        self, event_type: str | None = None, limit: int = 100
    ) -> Sequence[EventModel]:
        """Fetch recent events with optional type filter."""
        stmt = select(EventModel)
        if event_type:
            stmt = stmt.where(EventModel.event_type == event_type)
        stmt = stmt.order_by(EventModel.timestamp.desc()).limit(limit)
        return self.db.scalars(stmt).all()
