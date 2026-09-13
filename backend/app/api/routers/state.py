"""
API router for inspecting and patching World State.
"""

from typing import Any
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.models import WorldState
from app.services import StateService

router = APIRouter(prefix="/state", tags=["state"])


class PatchStateRequest(BaseModel):
    context: dict[str, Any] = Field(default_factory=dict)
    metrics: dict[str, float] = Field(default_factory=dict)


@router.get("", response_model=WorldState)
def get_state() -> WorldState:
    """Get authoritative current World State."""
    svc = StateService()
    return svc.get_current_state()


@router.patch("", response_model=WorldState)
async def patch_state(req: PatchStateRequest) -> WorldState:
    """Patch world state context and/or metrics."""
    svc = StateService()
    if req.metrics:
        await svc.update_metrics(req.metrics)
    if req.context:
        await svc.update_state_context(req.context)
    return svc.get_current_state()
