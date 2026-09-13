"""
SQLAlchemy ORM model for world state snapshots.
"""

from datetime import datetime, timezone
import uuid
from typing import Any

from sqlalchemy import String, DateTime, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class WorldStateSnapshotModel(Base):
    """Point-in-time state snapshot of the monitored environment."""

    __tablename__ = "world_state_snapshots"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    incident_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("incidents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    phase: Mapped[str] = mapped_column(String(50), nullable=False, default="idle")
    active_plan_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, index=True
    )
    metrics_json: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    context_json: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
