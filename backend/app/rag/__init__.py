"""
app/rag package — Retrieval-Augmented Generation support.

RAG is NOT implemented in the foundation phase.
This package defines the interface for future implementation.

The RAG layer provides the planner with relevant runbooks and postmortem
documents retrieved from a ChromaDB vector store.
"""

from __future__ import annotations

import abc


class BaseRetriever(abc.ABC):
    """Abstract retriever interface."""

    @abc.abstractmethod
    async def retrieve(self, query: str, *, top_k: int = 5) -> list[dict]:
        """Retrieve the top-k documents most relevant to *query*.

        Args:
            query:  Natural-language query string.
            top_k:  Maximum number of documents to return.

        Returns:
            A list of dicts, each with at minimum ``{"content": str, "score": float}``.
        """

    @abc.abstractmethod
    async def ingest(self, documents: list[dict]) -> int:
        """Ingest documents into the vector store.

        Args:
            documents: List of dicts with at minimum ``{"content": str}``.

        Returns:
            Number of documents successfully ingested.
        """
