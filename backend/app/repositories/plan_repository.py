"""
Repository for plan and plan step persistence.
"""

from datetime import datetime, timezone
from typing import Sequence
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models.plan import PlanModel, PlanStepModel
from app.repositories.base import BaseRepository


class PlanRepository(BaseRepository[PlanModel]):
    """Repository managing response plans and associated plan steps."""

    def __init__(self, db: Session) -> None:
        super().__init__(PlanModel, db)

    def get_plan_with_steps(self, plan_id: str) -> PlanModel | None:
        """Fetch plan by ID including preloaded steps."""
        stmt = (
            select(PlanModel)
            .options(selectinload(PlanModel.steps))
            .where(PlanModel.id == plan_id)
        )
        return self.db.scalars(stmt).first()

    def get_plans_for_incident(self, incident_id: str) -> Sequence[PlanModel]:
        """Fetch all plans generated for an incident."""
        stmt = (
            select(PlanModel)
            .options(selectinload(PlanModel.steps))
            .where(PlanModel.incident_id == incident_id)
            .order_by(PlanModel.created_at.desc())
        )
        return self.db.scalars(stmt).all()

    def update_plan_status(self, plan_id: str, status: str) -> PlanModel | None:
        """Update lifecycle status of a plan."""
        plan = self.get_by_id(plan_id)
        if not plan:
            return None
        plan.status = status
        plan.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(plan)
        return plan

    def update_step_status(self, step_id: str, status: str) -> PlanStepModel | None:
        """Update status of an individual step."""
        step = self.db.get(PlanStepModel, step_id)
        if not step:
            return None
        step.status = status
        self.db.commit()
        self.db.refresh(step)
        return step
