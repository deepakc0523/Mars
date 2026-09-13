"""
Incident lifecycle management service.
"""

from __future__ import annotations

import logging
from uuid import UUID
from sqlalchemy.orm import Session

from app.db.models.incident import IncidentModel
from app.events.factory import make_alert_event
from app.models import IncidentStatus
from app.repositories import IncidentRepository
from app.state.lifecycle import validate_lifecycle_transition
from app.state.manager import state_manager

log = logging.getLogger(__name__)


class IncidentService:
    """Service encapsulating incident creation, query, and lifecycle status transitions."""

    async def create_incident(
        self,
        title: str,
        description: str = "",
        severity: str = "medium",
        metadata: dict | None = None,
        *,
        db: Session,
    ) -> IncidentModel:
        """Create a new incident and update active world state."""
        repo = IncidentRepository(db)
        incident = repo.create(
            IncidentModel(
                title=title,
                description=description,
                severity=severity,
                status=IncidentStatus.DETECTED.value,
                metadata_json=metadata or {},
            )
        )
        await state_manager.set_incident(UUID(incident.id))
        await state_manager.set_incident_status(IncidentStatus.DETECTED)

        log.info("IncidentService: created incident id=%s title='%s'", incident.id, title)
        return incident

    def get_incident(self, incident_id: str, db: Session) -> IncidentModel | None:
        """Fetch incident by primary key ID."""
        repo = IncidentRepository(db)
        return repo.get_by_id(incident_id)

    async def update_status(
        self,
        incident_id: str,
        target_status: IncidentStatus | str,
        db: Session,
        *,
        is_reopen_event: bool = False,
    ) -> IncidentModel:
        """
        Validate lifecycle status transition and apply update.

        Raises InvalidLifecycleTransitionError if transition is forbidden.
        """
        repo = IncidentRepository(db)
        incident = repo.get_by_id(incident_id)
        if not incident:
            raise ValueError(f"Incident with ID '{incident_id}' not found.")

        current_status = IncidentStatus(incident.status)
        new_status = validate_lifecycle_transition(
            current_status, target_status, is_reopen_event=is_reopen_event
        )

        incident = repo.update(incident, status=new_status.value)
        await state_manager.set_incident_status(new_status, is_reopen_event=is_reopen_event)

        log.info(
            "IncidentService: status transition id=%s %s -> %s",
            incident_id,
            current_status.value,
            new_status.value,
        )

        # Emit audit event
        audit_event = make_alert_event(
            message=f"Incident '{incident.id}' status changed from '{current_status.value}' to '{new_status.value}'",
            severity="info",
            correlation_id=UUID(incident.id),
        )
        # Import inside method to avoid circular dependency
        from app.services.event_service import EventService
        await EventService().process_event(audit_event, db)

        return incident
