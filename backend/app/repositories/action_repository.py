"""
Repository for recording tool and action executions.
"""

from datetime import datetime, timezone
from typing import Any, Sequence
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.action import ActionModel
from app.repositories.base import BaseRepository


class ActionRepository(BaseRepository[ActionModel]):
    """Repository handling execution logs for actions."""

    def __init__(self, db: Session) -> None:
        super().__init__(ActionModel, db)

    def get_actions_for_plan(self, plan_id: str) -> Sequence[ActionModel]:
        """Fetch all action logs associated with a plan."""
        stmt = (
            select(ActionModel)
            .where(ActionModel.plan_id == plan_id)
            .order_by(ActionModel.started_at.asc())
        )
        return self.db.scalars(stmt).all()

    def complete_action(
        self,
        action_id: str,
        output_payload: dict[str, Any] | None = None,
        status: str = "completed",
        error_message: str | None = None,
    ) -> ActionModel | None:
        """Mark an action execution as completed or failed."""
        action = self.get_by_id(action_id)
        if not action:
            return None
        action.output_payload_json = output_payload
        action.status = status
        action.error_message = error_message
        action.completed_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(action)
        return action
