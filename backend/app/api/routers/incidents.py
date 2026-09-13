"""
API router for incident creation and status lifecycle management.
"""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models import IncidentStatus
from app.services import IncidentService

router = APIRouter(prefix="/incidents", tags=["incidents"])


class CreateIncidentRequest(BaseModel):
    title: str = Field(..., description="Short title of the incident.")
    description: str = Field(default="", description="Detailed description.")
    severity: str = Field(default="medium", description="Severity level.")
    metadata: dict[str, Any] = Field(default_factory=dict)


class UpdateIncidentStatusRequest(BaseModel):
    status: IncidentStatus = Field(..., description="Target lifecycle status.")
    is_reopen_event: bool = Field(
        default=False,
        description="Must be True if reopening a RESOLVED incident (RESOLVED -> DETECTED).",
    )


@router.post("", status_code=201)
async def create_incident(
    req: CreateIncidentRequest, db: Session = Depends(get_db)
) -> dict[str, Any]:
    """Create a new incident record."""
    svc = IncidentService()
    incident = await svc.create_incident(
        title=req.title,
        description=req.description,
        severity=req.severity,
        metadata=req.metadata,
        db=db,
    )
    return {
        "id": incident.id,
        "title": incident.title,
        "description": incident.description,
        "severity": incident.severity,
        "status": incident.status,
        "created_at": incident.created_at.isoformat(),
    }


@router.get("/{incident_id}")
def get_incident(incident_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Retrieve details for a specific incident."""
    svc = IncidentService()
    incident = svc.get_incident(incident_id, db)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident '{incident_id}' not found.",
        )
    return {
        "id": incident.id,
        "title": incident.title,
        "description": incident.description,
        "severity": incident.severity,
        "status": incident.status,
        "metadata": incident.metadata_json,
        "created_at": incident.created_at.isoformat(),
        "updated_at": incident.updated_at.isoformat(),
        "resolved_at": incident.resolved_at.isoformat() if incident.resolved_at else None,
    }


@router.patch("/{incident_id}/status")
async def update_incident_status(
    incident_id: str,
    req: UpdateIncidentStatusRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Update incident lifecycle status strictly enforcing transition rules."""
    svc = IncidentService()
    try:
        updated = await svc.update_status(
            incident_id=incident_id,
            target_status=req.status,
            db=db,
            is_reopen_event=req.is_reopen_event,
        )
        return {
            "id": updated.id,
            "status": updated.status,
            "updated_at": updated.updated_at.isoformat(),
        }
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
