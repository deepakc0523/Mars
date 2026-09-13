"""
SQLAlchemy ORM models for plans and plan steps.
"""

from datetime import datetime, timezone
import uuid
from typing import Any, List

from sqlalchemy import String, DateTime, Text, Integer, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class PlanModel(Base):
    """Structured response plan formulated to resolve an incident."""

    __tablename__ = "plans"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    incident_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rationale: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    steps: Mapped[List["PlanStepModel"]] = relationship(
        "PlanStepModel",
        back_populates="plan",
        cascade="all, delete-orphan",
        order_by="PlanStepModel.step_index",
    )


class PlanStepModel(Base):
    """Atomic step contained within a response plan."""

    __tablename__ = "plan_steps"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    plan_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    tool: Mapped[str] = mapped_column(String(100), nullable=False)
    parameters_json: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    expected_outcome: Mapped[str] = mapped_column(Text, nullable=False, default="")
    estimated_duration_seconds: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")

    plan: Mapped[PlanModel] = relationship("PlanModel", back_populates="steps")
