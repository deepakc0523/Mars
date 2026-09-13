"""
End-to-End Core Integration Scenario Test for MARS Phase 3A — INC-1042 Plan Execution.

Scenario:
  Incident: INC-1042 (Payment API degradation)
  Plan: PLAN-001 (S1 retrieve_api_logs, S2 analyze_error_patterns, S3 investigate_database, S4 compare_recent_deployment)

  Execution:
    Sequential execution of S1 -> S2 -> S3 -> S4 via ActionController.

  Verifications:
    1. S1, S2, S3, S4 all reach COMPLETED status.
    2. ExecutionContext status becomes 'completed'.
    3. WorldState.active_action is cleared (None) upon completion.
    4. 4 ActionModel records persisted in SQLite actions table.
    5. WebSocket manager receives broadcasts for action execution events.
    6. REST execution endpoint /execution/plans/{id}/status reflects 100% completion.
"""

from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient

from app.api.application import create_app
from app.db.database import SessionLocal, init_db
from app.db.models.action import ActionModel
from app.execution import ActionController
from app.models import PlanStepStatus
from app.services import IncidentService, PlanService
from app.state.manager import state_manager
from app.ws.manager import ws_manager


@pytest.mark.anyio
async def test_inc1042_full_execution_scenario():
    """Execute complete sequential plan execution for INC-1042 scenario."""
    init_db()
    db = SessionLocal()
    await state_manager.reset()

    try:
        # Step 1: Create incident INC-1042
        inc_svc = IncidentService()
        incident = await inc_svc.create_incident(
            title="Payment API degradation",
            description="High latency on payment gateway",
            severity="critical",
            db=db,
        )
        incident_id = incident.id

        # Step 2: Create initial plan PLAN-001 (S1, S2, S3, S4)
        plan_svc = PlanService()
        steps_data = [
            {"description": "Retrieve API gateway logs", "tool": "retrieve_api_logs"},
            {"description": "Analyze error patterns in APM", "tool": "analyze_error_patterns"},
            {"description": "Investigate database query performance", "tool": "investigate_database"},
            {"description": "Compare recent deployment diffs", "tool": "compare_recent_deployment"},
        ]
        plan = await plan_svc.create_plan(
            incident_id=incident_id,
            steps_data=steps_data,
            rationale="Standard triage plan",
            db=db,
        )
        plan_id = plan.id

        # Step 3: Mock WebSocket manager to verify live broadcasts
        with patch.object(ws_manager, "broadcast", new=AsyncMock()) as mock_broadcast:
            controller = ActionController()

            # Step 4: Execute plan
            context = await controller.execute_plan(plan_id, db=db)

            # VERIFICATION 1: ExecutionContext status completed
            assert context.status == "completed"
            assert len(context.completed_steps) == 4
            assert len(context.failed_steps) == 0

            # VERIFICATION 2: All steps in DB marked COMPLETED
            updated_plan = plan_svc.get_plan(plan_id, db)
            assert updated_plan is not None
            for step in updated_plan.steps:
                assert step.status == PlanStepStatus.COMPLETED.value

            # VERIFICATION 3: WorldState active_action cleared (None)
            current_ws = state_manager.current
            assert current_ws.active_action is None

            # VERIFICATION 4: 4 ActionModel records persisted in SQLite
            actions = db.query(ActionModel).filter_by(plan_id=plan_id).all()
            assert len(actions) == 4
            tools_executed = [a.tool_name for a in actions]
            assert tools_executed == [
                "retrieve_api_logs",
                "analyze_error_patterns",
                "investigate_database",
                "compare_recent_deployment",
            ]
            for action in actions:
                assert action.status == "completed"
                assert action.output_payload_json is not None
                assert action.output_payload_json.get("status") == "success"

            # VERIFICATION 5: WebSocket broadcasts received (8 broadcasts: 4 start + 4 complete)
            assert mock_broadcast.call_count >= 8

            # VERIFICATION 6: REST API status verification
            client = TestClient(create_app())
            status_res = client.get(f"/execution/plans/{plan_id}/status")
            assert status_res.status_code == 200
            res_json = status_res.json()
            assert res_json["completed_count"] == 4
            assert res_json["failed_count"] == 0

    finally:
        db.close()
