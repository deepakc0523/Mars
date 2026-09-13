"""
Repository for incident management operations.
"""

from datetime import datetime, timezone
from typing import Sequence
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.incident import IncidentModel
from app.repositories.base import BaseRepository


class IncidentRepository(BaseRepository[IncidentModel]):
    """Repository handling database operations for incidents."""

    def __init__(self, db: Session) -> None:
        super().__init__(IncidentModel, db)

    def get_active_incidents(self) -> Sequence[IncidentModel]:
        """Fetch all currently active incidents."""
        stmt = select(IncidentModel).where(IncidentModel.status == "active").order_by(IncidentModel.created_at.desc())
        return self.db.scalars(stmt).all()

    def resolve_incident(self, incident_id: str) -> IncidentModel | None:
        """Mark an incident as resolved with resolution timestamp."""
        incident = self.get_by_id(incident_id)
        if not incident:
            return None
        now = datetime.now(timezone.utc)
        incident.status = "resolved"
        incident.resolved_at = now
        incident.updated_at = now
        self.db.commit()
        self.db.refresh(incident)
        return incident
