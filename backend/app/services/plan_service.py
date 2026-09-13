"""
Plan management and mutation service for MARS.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID, uuid4
from sqlalchemy.orm import Session

from app.db.models.plan import PlanModel, PlanStepModel
from app.events.factory import make_plan_created_event, make_plan_updated_event
from app.models import PlanStepStatus
from app.repositories import PlanRepository
from app.state.manager import state_manager

log = logging.getLogger(__name__)


class PlanService:
    """Service handling plan creation, retrieval, and non-destructive step mutations."""

    async def create_plan(
        self,
        incident_id: str,
        steps_data: list[dict[str, Any]],
        rationale: str = "",
        *,
        db: Session,
    ) -> PlanModel:
        """Create a new plan and persist its steps."""
        repo = PlanRepository(db)
        plan = PlanModel(
            incident_id=incident_id,
            rationale=rationale,
            status="pending",
        )
        saved_plan = repo.create(plan)

        step_models = []
        for idx, step_dict in enumerate(steps_data):
            step = PlanStepModel(
                id=str(step_dict.get("step_id", uuid4())),
                plan_id=saved_plan.id,
                step_index=idx,
                description=step_dict.get("description", ""),
                tool=step_dict.get("tool", ""),
                parameters_json=step_dict.get("parameters", {}),
                expected_outcome=step_dict.get("expected_outcome", ""),
                estimated_duration_seconds=step_dict.get("estimated_duration_seconds"),
                status=step_dict.get("status", PlanStepStatus.PENDING.value),
            )
            db.add(step)
            step_models.append(step)

        db.commit()
        db.refresh(saved_plan)

        await state_manager.set_active_plan(UUID(saved_plan.id))

        # Emit PLAN_CREATED event
        from app.services.event_service import EventService
        steps_payload = [
            {
                "step_id": s.id,
                "step_index": s.step_index,
                "description": s.description,
                "tool": s.tool,
                "status": s.status,
            }
            for s in saved_plan.steps
        ]
        evt = make_plan_created_event(
            plan_id=saved_plan.id,
            incident_id=incident_id,
            steps=steps_payload,
            rationale=rationale,
            correlation_id=UUID(incident_id) if incident_id else None,
        )
        await EventService().process_event(evt, db)

        return saved_plan

    def get_plan(self, plan_id: str, db: Session) -> PlanModel | None:
        """Fetch plan by ID including steps."""
        repo = PlanRepository(db)
        return repo.get_plan_with_steps(plan_id)

    def get_active_step(self, plan: PlanModel) -> PlanStepModel | None:
        """Identify the currently active (in_progress or first pending) step in a plan."""
        sorted_steps = sorted(plan.steps, key=lambda s: s.step_index)
        for step in sorted_steps:
            if step.status == PlanStepStatus.IN_PROGRESS.value:
                return step
        for step in sorted_steps:
            if step.status == PlanStepStatus.PENDING.value:
                return step
        return None

    async def add_step(
        self,
        plan_id: str,
        step_data: dict[str, Any],
        db: Session,
    ) -> PlanModel:
        """Append a new step at the end of the plan."""
        repo = PlanRepository(db)
        plan = repo.get_plan_with_steps(plan_id)
        if not plan:
            raise ValueError(f"Plan '{plan_id}' not found.")

        next_idx = max([s.step_index for s in plan.steps], default=-1) + 1
        new_step = PlanStepModel(
            id=str(step_data.get("step_id", uuid4())),
            plan_id=plan.id,
            step_index=next_idx,
            description=step_data.get("description", ""),
            tool=step_data.get("tool", ""),
            parameters_json=step_data.get("parameters", {}),
            expected_outcome=step_data.get("expected_outcome", ""),
            estimated_duration_seconds=step_data.get("estimated_duration_seconds"),
            status=PlanStepStatus.PENDING.value,
        )
        db.add(new_step)
        db.commit()
        db.refresh(plan)

        await self._notify_plan_updated(plan, db)
        return plan

    async def insert_step(
        self,
        plan_id: str,
        target_index: int,
        step_data: dict[str, Any],
        db: Session,
    ) -> PlanModel:
        """Insert a step at target_index, shifting existing steps non-destructively."""
        repo = PlanRepository(db)
        plan = repo.get_plan_with_steps(plan_id)
        if not plan:
            raise ValueError(f"Plan '{plan_id}' not found.")

        # Shift indices of steps at or after target_index
        for s in plan.steps:
            if s.step_index >= target_index:
                s.step_index += 1

        new_step = PlanStepModel(
            id=str(step_data.get("step_id", uuid4())),
            plan_id=plan.id,
            step_index=target_index,
            description=step_data.get("description", ""),
            tool=step_data.get("tool", ""),
            parameters_json=step_data.get("parameters", {}),
            expected_outcome=step_data.get("expected_outcome", ""),
            estimated_duration_seconds=step_data.get("estimated_duration_seconds"),
            status=PlanStepStatus.PENDING.value,
        )
        db.add(new_step)
        db.commit()
        db.refresh(plan)

        await self._notify_plan_updated(plan, db)
        return plan

    async def cancel_step(
        self,
        plan_id: str,
        step_identifier: str,
        db: Session,
    ) -> PlanModel:
        """
        Cancel a step by step_id or tool name.

        Preserves historical steps and status; does NOT delete steps from the database.
        """
        repo = PlanRepository(db)
        plan = repo.get_plan_with_steps(plan_id)
        if not plan:
            raise ValueError(f"Plan '{plan_id}' not found.")

        target_step = None
        for step in plan.steps:
            if step.id == step_identifier or step.tool == step_identifier:
                target_step = step
                break

        if target_step:
            target_step.status = PlanStepStatus.CANCELLED.value
            db.commit()
            db.refresh(plan)
            log.info("PlanService: cancelled step id=%s tool=%s in plan id=%s", target_step.id, target_step.tool, plan.id)

        await self._notify_plan_updated(plan, db)
        return plan

    async def _notify_plan_updated(self, plan: PlanModel, db: Session) -> None:
        """Emit PLAN_UPDATED event via EventService."""
        from app.services.event_service import EventService
        steps_payload = [
            {
                "step_id": s.id,
                "step_index": s.step_index,
                "description": s.description,
                "tool": s.tool,
                "status": s.status,
            }
            for s in sorted(plan.steps, key=lambda x: x.step_index)
        ]
        evt = make_plan_updated_event(
            plan_id=plan.id,
            incident_id=plan.incident_id,
            steps=steps_payload,
            rationale=plan.rationale,
            correlation_id=UUID(plan.incident_id) if plan.incident_id else None,
        )
        await EventService().process_event(evt, db)
