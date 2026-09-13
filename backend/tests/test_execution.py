"""
Unit and integration tests for Phase 3A ActionController, Simulated Environment, and Execution REST APIs.
"""

from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient

from app.api.application import create_app
from app.db.database import SessionLocal, init_db
from app.db.models.action import ActionModel
from app.execution import ActionController, SimulatedEnvironment, tool_registry
from app.models import ExecutionContext, PlanStepStatus
from app.services import IncidentService, PlanService
from app.state.manager import state_manager
from app.ws.manager import ws_manager


def test_simulated_environment_initialization():
    """Test environment initialization and deterministic outputs."""
    env = SimulatedEnvironment()
    assert env.error_rate == 18.0
    assert env.database_health == "healthy"

    logs = env.get_api_logs(limit=2)
    assert len(logs) == 2
    assert "Gateway Timeout" in logs[0]["message"]

    db_metrics = env.get_database_status()
    assert db_metrics["status"] == "healthy"


def test_tool_registry_and_deterministic_tools():
    """Test deterministic tool executions via ToolRegistry."""
    env = SimulatedEnvironment()

    log_tool = tool_registry.get_tool("retrieve_api_logs")
    res1 = log_tool.execute(env, {"limit": 5})
    assert res1["status"] == "success"
    assert res1["log_count"] == 3

    db_tool = tool_registry.get_tool("investigate_database")
    res2 = db_tool.execute(env, {})
    assert res2["status"] == "success"
    assert res2["database_metrics"]["status"] == "healthy"


@pytest.mark.anyio
async def test_action_controller_single_step_execution():
    """Test single step execution lifecycle, persistence, and state updates."""
    init_db()
    db = SessionLocal()
    await state_manager.reset()

    try:
        inc_svc = IncidentService()
        inc = await inc_svc.create_incident(title="Single Action Test", db=db)

        plan_svc = PlanService()
        plan = await plan_svc.create_plan(
            incident_id=inc.id,
            steps_data=[{"description": "Check gateway", "tool": "check_payment_gateway"}],
            db=db,
        )

        controller = ActionController()
        context = ExecutionContext(plan_id=plan.id)
        step = plan.steps[0]

        action_record, success = await controller.execute_step(plan.id, step, context, db)

        assert success is True
        assert action_record.status == "completed"
        assert step.status == PlanStepStatus.COMPLETED.value
        assert len(context.completed_steps) == 1
        assert state_manager.current.active_action is None

        # Verify ActionModel in DB
        db_action = db.query(ActionModel).filter_by(id=action_record.id).first()
        assert db_action is not None
        assert db_action.tool_name == "check_payment_gateway"
        assert db_action.status == "completed"

    finally:
        db.close()


@pytest.mark.anyio
async def test_action_controller_failure_handling():
    """Test failure path handling: failing action, failed step, execution halt, completed steps preserved."""
    init_db()
    db = SessionLocal()
    await state_manager.reset()

    try:
        inc_svc = IncidentService()
        inc = await inc_svc.create_incident(title="Failure Path Test", db=db)

        plan_svc = PlanService()
        plan = await plan_svc.create_plan(
            incident_id=inc.id,
            steps_data=[
                {"description": "Retrieve logs", "tool": "retrieve_api_logs"},
                {"description": "Invoke failing tool", "tool": "failing_mock_tool"},
                {"description": "Unreachable step", "tool": "compare_recent_deployment"},
            ],
            db=db,
        )

        controller = ActionController()
        context = await controller.execute_plan(plan.id, db)

        assert context.status == "failed"
        assert len(context.completed_steps) == 1
        assert len(context.failed_steps) == 1

        # Check step statuses
        updated_plan = plan_svc.get_plan(plan.id, db)
        steps_by_tool = {s.tool: s for s in updated_plan.steps}

        assert steps_by_tool["retrieve_api_logs"].status == PlanStepStatus.COMPLETED.value
        assert steps_by_tool["failing_mock_tool"].status == PlanStepStatus.FAILED.value
        assert steps_by_tool["compare_recent_deployment"].status == PlanStepStatus.PENDING.value

        # Check Action records in DB
        actions = db.query(ActionModel).filter_by(plan_id=plan.id).all()
        assert len(actions) == 2
        failed_action = [a for a in actions if a.tool_name == "failing_mock_tool"][0]
        assert failed_action.status == "failed"
        assert "Simulated tool execution failure" in failed_action.error_message

    finally:
        db.close()


def test_rest_execution_endpoints():
    """Test REST execution APIs (/execution/plans/{id}/run, /status, /actions/{id})."""
    init_db()
    client = TestClient(create_app())

    # 1. Create incident & plan
    inc_res = client.post("/incidents", json={"title": "REST Exec Test"})
    inc_id = inc_res.json()["id"]

    plan_res = client.post(
        "/plans",
        json={
            "incident_id": inc_id,
            "steps": [{"description": "Check dependency", "tool": "check_dependency_health"}],
        },
    )
    plan_id = plan_res.json()["id"]

    # 2. Run execution via POST /execution/plans/{id}/run
    run_res = client.post(f"/execution/plans/{plan_id}/run")
    assert run_res.status_code == 200
    run_json = run_res.json()
    assert run_json["status"] == "completed"

    # 3. Check status via GET /execution/plans/{id}/status
    status_res = client.get(f"/execution/plans/{plan_id}/status")
    assert status_res.status_code == 200
    assert status_res.json()["completed_count"] == 1

    # 4. Check action detail via GET /execution/actions/{action_id}
    db = SessionLocal()
    try:
        action = db.query(ActionModel).filter_by(plan_id=plan_id).first()
        assert action is not None
        act_detail = client.get(f"/execution/actions/{action.id}")
        assert act_detail.status_code == 200
        assert act_detail.json()["tool_name"] == "check_dependency_health"
        assert act_detail.json()["status"] == "completed"
    finally:
        db.close()
