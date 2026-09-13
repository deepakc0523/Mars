"""
Tests for StateManager.
"""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest

from app.models import AgentPhase
from app.state import StateManager


class TestStateManager:
    def _run(self, coro):  # type: ignore[no-untyped-def]
        return asyncio.run(coro)

    def test_initial_phase_is_idle(self) -> None:
        sm = StateManager()
        assert sm.current.phase == AgentPhase.IDLE

    def test_transition_phase(self) -> None:
        sm = StateManager()
        self._run(sm.transition_phase(AgentPhase.INTERRUPT))
        assert sm.current.phase == AgentPhase.INTERRUPT

    def test_update_metrics(self) -> None:
        sm = StateManager()
        self._run(sm.update_metrics({"error_rate": 0.12}))
        assert sm.current.metrics["error_rate"] == pytest.approx(0.12)

    def test_update_metrics_merges(self) -> None:
        sm = StateManager()
        self._run(sm.update_metrics({"a": 1.0}))
        self._run(sm.update_metrics({"b": 2.0}))
        assert "a" in sm.current.metrics
        assert "b" in sm.current.metrics

    def test_set_active_plan(self) -> None:
        sm = StateManager()
        plan_id = uuid4()
        self._run(sm.set_active_plan(plan_id))
        assert sm.current.active_plan_id == plan_id

    def test_reset_returns_to_idle(self) -> None:
        sm = StateManager()
        self._run(sm.transition_phase(AgentPhase.EXECUTE))
        self._run(sm.reset())
        assert sm.current.phase == AgentPhase.IDLE
        assert sm.current.active_plan_id is None

    def test_current_returns_copy(self) -> None:
        sm = StateManager()
        a = sm.current
        b = sm.current
        assert a is not b
