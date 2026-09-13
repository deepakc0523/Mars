"""
API router for plan execution, status inspection, and action log queries.
"""

from typing import Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.execution import ActionController
from app.models import ExecutionContext, PlanStepStatus
from app.repositories import ActionRepository, PlanRepository

router = APIRouter(prefix="/execution", tags=["execution"])


@router.post("/plans/{plan_id}/run", response_model=ExecutionContext)
async def run_plan_execution(
    plan_id: str, db: Session = Depends(get_db)
) -> ExecutionContext:
    """Trigger sequential execution of all pending steps in a plan."""
    controller = ActionController()
    try:
        context = await controller.execute_plan(plan_id, db)
        return context
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/plans/{plan_id}/status", response_model=dict[str, Any])
def get_plan_execution_status(
    plan_id: str, db: Session = Depends(get_db)
) -> dict[str, Any]:
    """Retrieve execution status and progress summary for a plan."""
    repo = PlanRepository(db)
    plan = repo.get_plan_with_steps(plan_id)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan '{plan_id}' not found.",
        )

    sorted_steps = sorted(plan.steps, key=lambda s: s.step_index)
    completed_steps = [s.id for s in sorted_steps if s.status == PlanStepStatus.COMPLETED.value]
    failed_steps = [s.id for s in sorted_steps if s.status == PlanStepStatus.FAILED.value]
    pending_steps = [s.id for s in sorted_steps if s.status == PlanStepStatus.PENDING.value]
    in_progress = [s.id for s in sorted_steps if s.status == PlanStepStatus.IN_PROGRESS.value]

    return {
        "plan_id": plan.id,
        "incident_id": plan.incident_id,
        "plan_status": plan.status,
        "total_steps": len(plan.steps),
        "completed_count": len(completed_steps),
        "failed_count": len(failed_steps),
        "pending_count": len(pending_steps),
        "in_progress_count": len(in_progress),
        "completed_step_ids": completed_steps,
        "failed_step_ids": failed_steps,
        "pending_step_ids": pending_steps,
    }


@router.get("/actions/{action_id}", response_model=dict[str, Any])
def get_action_details(
    action_id: str, db: Session = Depends(get_db)
) -> dict[str, Any]:
    """Retrieve execution logs and details for an individual action."""
    repo = ActionRepository(db)
    action = repo.get_by_id(action_id)
    if not action:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Action record '{action_id}' not found.",
        )

    return {
        "id": action.id,
        "plan_id": action.plan_id,
        "step_id": action.step_id,
        "tool_name": action.tool_name,
        "input_payload": action.input_payload_json,
        "output_payload": action.output_payload_json,
        "status": action.status,
        "started_at": action.started_at.isoformat(),
        "completed_at": action.completed_at.isoformat() if action.completed_at else None,
        "error_message": action.error_message,
    }
