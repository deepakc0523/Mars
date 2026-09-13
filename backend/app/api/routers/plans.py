"""
API router for plan creation, generation, retrieval, and step mutations.
"""

from typing import Any, Literal
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services import PlanService, PlanningService

router = APIRouter(prefix="/plans", tags=["plans"])


class CreatePlanRequest(BaseModel):
    incident_id: str = Field(..., description="Incident ID this plan is created for.")
    rationale: str = Field(default="", description="Reasoning for this plan.")
    steps: list[dict[str, Any]] = Field(default_factory=list, description="Ordered list of steps.")


class GeneratePlanRequest(BaseModel):
    incident_id: str = Field(..., description="Incident ID to generate a plan for.")


class MutatePlanRequest(BaseModel):
    action: Literal["add_step", "insert_step", "cancel_step", "update_step_status"] = Field(
        ..., description="Type of mutation to apply."
    )
    target_index: int | None = Field(default=None, description="Index for insert_step.")
    step_identifier: str | None = Field(
        default=None, description="Step ID or tool name for cancel_step / update_step_status."
    )
    step_data: dict[str, Any] = Field(
        default_factory=dict, description="Step payload for add_step or insert_step."
    )
    status: str | None = Field(default=None, description="Status for update_step_status.")


@router.post("", status_code=201)
async def create_plan(
    req: CreatePlanRequest, db: Session = Depends(get_db)
) -> dict[str, Any]:
    """Create a new plan and record steps."""
    svc = PlanService()
    plan = await svc.create_plan(
        incident_id=req.incident_id,
        steps_data=req.steps,
        rationale=req.rationale,
        db=db,
    )
    return {
        "id": plan.id,
        "incident_id": plan.incident_id,
        "status": plan.status,
        "rationale": plan.rationale,
        "steps_count": len(plan.steps),
    }


@router.post("/generate", status_code=200)
async def generate_plan(
    req: GeneratePlanRequest, db: Session = Depends(get_db)
) -> dict[str, Any]:
    """
    Generate and verify a response plan for an incident through the Planner + Verifier state machine.
    """
    svc = PlanningService()
    plan, verification_result, planning_state, attempts = (
        await svc.generate_and_orchestrate_plan(req.incident_id, db=db)
    )

    plan_dict = None
    if plan:
        plan_svc = PlanService()
        active_step = plan_svc.get_active_step(plan)
        sorted_steps = sorted(plan.steps, key=lambda s: s.step_index)
        plan_dict = {
            "id": plan.id,
            "incident_id": plan.incident_id,
            "status": plan.status,
            "rationale": plan.rationale,
            "created_at": plan.created_at.isoformat(),
            "active_step": {
                "id": active_step.id,
                "step_index": active_step.step_index,
                "tool": active_step.tool,
                "status": active_step.status,
            } if active_step else None,
            "steps": [
                {
                    "id": s.id,
                    "step_index": s.step_index,
                    "description": s.description,
                    "tool": s.tool,
                    "parameters": s.parameters_json,
                    "expected_outcome": s.expected_outcome,
                    "status": s.status,
                }
                for s in sorted_steps
            ],
        }

    return {
        "status": "approved" if planning_state.value == "approved" else "failed",
        "planning_state": planning_state.value,
        "attempts": attempts,
        "plan": plan_dict,
        "verification_result": verification_result.model_dump(mode="json") if verification_result else None,
    }


@router.get("/{plan_id}")
def get_plan(plan_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Retrieve full plan with step ordering and statuses."""
    svc = PlanService()
    plan = svc.get_plan(plan_id, db)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan '{plan_id}' not found.",
        )
    active_step = svc.get_active_step(plan)
    sorted_steps = sorted(plan.steps, key=lambda s: s.step_index)
    return {
        "id": plan.id,
        "incident_id": plan.incident_id,
        "status": plan.status,
        "rationale": plan.rationale,
        "created_at": plan.created_at.isoformat(),
        "active_step": {
            "id": active_step.id,
            "step_index": active_step.step_index,
            "tool": active_step.tool,
            "status": active_step.status,
        } if active_step else None,
        "steps": [
            {
                "id": s.id,
                "step_index": s.step_index,
                "description": s.description,
                "tool": s.tool,
                "parameters": s.parameters_json,
                "expected_outcome": s.expected_outcome,
                "status": s.status,
            }
            for s in sorted_steps
        ],
    }


@router.patch("/{plan_id}")
async def mutate_plan(
    plan_id: str,
    req: MutatePlanRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Mutate plan steps non-destructively (add, insert, cancel)."""
    svc = PlanService()
    try:
        if req.action == "add_step":
            updated = await svc.add_step(plan_id, req.step_data, db)
        elif req.action == "insert_step":
            idx = req.target_index if req.target_index is not None else 0
            updated = await svc.insert_step(plan_id, idx, req.step_data, db)
        elif req.action == "cancel_step":
            ident = req.step_identifier or req.step_data.get("tool") or req.step_data.get("step_id")
            if not ident:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="step_identifier or tool name required for cancel_step.",
                )
            updated = await svc.cancel_step(plan_id, ident, db)
        elif req.action == "update_step_status":
            ident = req.step_identifier or req.step_data.get("step_id")
            if not ident or not req.status:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="step_identifier and status required for update_step_status.",
                )
            from app.repositories import PlanRepository
            PlanRepository(db).update_step_status(ident, req.status)
            updated = svc.get_plan(plan_id, db)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported mutation action '{req.action}'.",
            )

        return {
            "id": updated.id,
            "status": updated.status,
            "steps_count": len(updated.steps),
        }
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
