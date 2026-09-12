"""
app/tools package — callable tools available to agent plans.

Tools are NOT implemented in the foundation phase.
This package defines the registry interface.
"""

from __future__ import annotations

import abc
from typing import Any


class BaseTool(abc.ABC):
    """Abstract base for all MARS tools.

    Each tool exposes a ``name``, a ``description`` for the planner LLM,
    and an async ``execute`` method.
    """

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Machine-readable tool identifier used in plan steps."""

    @property
    @abc.abstractmethod
    def description(self) -> str:
        """Plain-English description shown to the planner LLM."""

    @abc.abstractmethod
    async def execute(self, **parameters: Any) -> dict[str, Any]:
        """Execute the tool with the given parameters.

        Returns:
            A dict containing at minimum ``{"success": bool}``.
        """
