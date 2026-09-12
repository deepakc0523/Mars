"""
app/ledger package — SHA-256 hash-chained decision ledger.

The ledger is NOT implemented in the foundation phase.
This package defines the interface for future implementation.

Every decision made by MARS (plan accepted/rejected, safety gate
pass/fail, execution result) is appended to an immutable, hash-chained
ledger stored in SQLite.  Any tampering with an entry breaks the chain.
"""

from __future__ import annotations

import abc
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class LedgerEntry(BaseModel):
    """A single immutable record in the decision ledger."""

    entry_id: UUID
    previous_hash: str = Field(description="SHA-256 hash of the previous entry.")
    entry_hash: str = Field(description="SHA-256 hash of this entry's content.")
    event_type: str
    payload: dict[str, Any]
    timestamp: datetime


class BaseLedger(abc.ABC):
    """Abstract ledger interface."""

    @abc.abstractmethod
    async def append(self, event_type: str, payload: dict[str, Any]) -> LedgerEntry:
        """Append a new entry to the ledger.

        Args:
            event_type: A string tag identifying the decision type.
            payload:    Arbitrary JSON-serialisable data.

        Returns:
            The newly created ``LedgerEntry``.
        """

    @abc.abstractmethod
    async def verify_chain(self) -> bool:
        """Verify that the entire ledger chain is intact.

        Returns:
            ``True`` if no entries have been tampered with.
        """

    @abc.abstractmethod
    async def get_entries(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[LedgerEntry]:
        """Retrieve ledger entries in chronological order."""
