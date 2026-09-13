"""
Unit and failure tests for Phase 2 Planner, Verifier, and PlanningService.
"""

from uuid import uuid4
import pytest
from fastapi.testclient import TestClient

from app.agents import MockPlanner, MockVerifier
from app.api.application import create_app
from app.db.database import SessionLocal, init_db
from app.models import AgentPhase, PlanStep, PlanStepStatus, PlanningState, ProposedPlan, WorldState
from app.services import IncidentService, PlanningService
from app.state.manager import state_manager


@pytest.mark.anyio
async def test_verifier_rejects_restricted_action():
    """Test that Verifier rejects plans containing prohibited/restricted tools."""
    verifier = MockVerifier()
    ws = WorldState(restrictions=["investigate_database"])

    plan = ProposedPlan(
        objective="Triage issue",
        steps=[
            PlanStep(tool="retrieve_api_logs", description="Get logs"),
            PlanStep(tool="investigate_database", description="Inspect DB"),
        ],
    )

    result = await verifier.verify(ws, plan)
    assert result.approved is False
    assert result.risk_level == "high"
    assert any("investigate_database" in issue for issue in result.issues)


@pytest.mark.anyio
async def test_verifier_rejects_empty_plan():
    """Test that Verifier rejects empty plans."""
    verifier = MockVerifier()
    ws = WorldState()
    plan = ProposedPlan(objective="Triage", steps=[])

    result = await verifier.verify(ws, plan)
    assert result.approved is False
    assert any("no steps" in issue.lower() for issue in result.issues)


@pytest.mark.anyio
async def test_verifier_flags_duplicate_and_missing_fields():
    """Test that Verifier flags duplicate tools and missing descriptions."""
    verifier = MockVerifier()
    ws = WorldState()
    plan = ProposedPlan(
        objective="Triage",
        steps=[
            PlanStep(tool="", description=""),
            PlanStep(tool="flush_cache", description="Flush cache"),
            PlanStep(tool="flush_cache", description="Flush cache again"),
        ],
    )

    result = await verifier.verify(ws, plan)
    assert result.approved is False
    assert len(result.issues) > 0
    assert len(result.warnings) > 0


@pytest.mark.anyio
async def test_bounded_replanning_max_attempts_failure():
    """Test that PlanningService halts after 3 failed attempts and reaches FAILED state."""
    init_db()
    db = SessionLocal()
    await state_manager.reset()

    try:
        inc_svc = IncidentService()
        inc = await inc_svc.create_incident(title="Failure Test Incident", db=db)

        # Force planner to generate restricted tool on every attempt
        bad_planner = MockPlanner(force_restricted_tool="prohibited_action")
        verifier = MockVerifier()

        planning_svc = PlanningService(planner=bad_planner, verifier=verifier)
        plan, ver_result, state, attempts = (
            await planning_svc.generate_and_orchestrate_plan(inc.id, db=db, max_attempts=3)
        )

        assert plan is None
        assert state == PlanningState.FAILED
        assert attempts == 3
        assert ver_result is not None
        assert ver_result.approved is False

    finally:
        db.close()


@pytest.mark.anyio
async def test_deterministic_planner_output():
    """Test that MockPlanner yields identical deterministic output for same inputs."""
    planner = MockPlanner()
    ws = WorldState(restrictions=["restart_service"])

    p1 = await planner.plan(ws)
    p2 = await planner.plan(ws)

    tools1 = [s.tool for s in p1.steps]
    tools2 = [s.tool for s in p2.steps]

    assert tools1 == tools2
    assert "restart_service" not in tools1


def test_post_plans_generate_api_endpoint():
    """Test POST /plans/generate REST endpoint."""
    init_db()
    client = TestClient(create_app())

    # 1. Create incident
    inc_res = client.post("/incidents", json={"title": "API Latency Spike"})
    assert inc_res.status_code == 201
    inc_id = inc_res.json()["id"]

    # 2. Generate plan via API
    gen_res = client.post("/plans/generate", json={"incident_id": inc_id})
    assert gen_res.status_code == 200
    res_data = gen_res.json()

    assert res_data["status"] == "approved"
    assert res_data["planning_state"] == "approved"
    assert res_data["attempts"] == 1
    assert res_data["plan"] is not None
    assert len(res_data["plan"]["steps"]) > 0
    assert res_data["verification_result"]["approved"] is True
