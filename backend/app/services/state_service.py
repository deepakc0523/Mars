"""
State Service for fetching and patching authoritative World State.
"""

from __future__ import annotations

from typing import Any
from sqlalchemy.orm import Session

from app.models import WorldState
from app.state.manager import state_manager


class StateService:
    """Service wrapping state retrieval and state context modifications."""

    def get_current_state(self) -> WorldState:
        """Return a copy of the current authoritative WorldState."""
        return state_manager.current

    async def update_state_context(self, context_updates: dict[str, Any]) -> WorldState:
        """Patch state context values."""
        return await state_manager.update_context(**context_updates)

    async def update_metrics(self, metrics: dict[str, float]) -> WorldState:
        """Merge metric updates into world state."""
        return await state_manager.update_metrics(metrics)
