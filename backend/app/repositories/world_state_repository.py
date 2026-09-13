"""
Repository for world state snapshot operations.
"""

from typing import Sequence
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.world_state import WorldStateSnapshotModel
from app.repositories.base import BaseRepository


class WorldStateRepository(BaseRepository[WorldStateSnapshotModel]):
    """Repository handling persistence and lookup for world state snapshots."""

    def __init__(self, db: Session) -> None:
        super().__init__(WorldStateSnapshotModel, db)

    def get_latest_snapshot(
        self, incident_id: str | None = None
    ) -> WorldStateSnapshotModel | None:
        """Fetch the most recent world state snapshot."""
        stmt = select(WorldStateSnapshotModel)
        if incident_id:
            stmt = stmt.where(WorldStateSnapshotModel.incident_id == incident_id)
        stmt = stmt.order_by(WorldStateSnapshotModel.timestamp.desc()).limit(1)
        return self.db.scalars(stmt).first()

    def list_snapshots_for_incident(
        self, incident_id: str, limit: int = 50
    ) -> Sequence[WorldStateSnapshotModel]:
        """Fetch historical snapshots for a specific incident."""
        stmt = (
            select(WorldStateSnapshotModel)
            .where(WorldStateSnapshotModel.incident_id == incident_id)
            .order_by(WorldStateSnapshotModel.timestamp.desc())
            .limit(limit)
        )
        return self.db.scalars(stmt).all()
