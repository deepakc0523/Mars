"""
End-to-End Core Integration Scenario Test for MARS — INC-1042.

Scenario:
  Incident: INC-1042
  Title: Payment API degradation
  Objective: Identify root cause and restore service

  Initial plan:
    S1 retrieve_api_logs          COMPLETED
    S2 analyze_error_patterns     COMPLETED
    S3 investigate_database       PENDING
    S4 compare_recent_deployment  PENDING

  Event: HUMAN_INTERRUPT ("Don't investigate the database.")

  Verifications:
    1. HUMAN_INTERRUPT event created & persisted to SQLite events table.
    2. Incident lifecycle status becomes INTERRUPTED.
    3. World State records restriction: "investigate_database".
    4. S3 step becomes CANCELLED.
    5. S4 step remains PENDING.
    6. New step S3.1 can be inserted into plan without deleting history.
    7. World State snapshot persisted in SQLite world_state_snapshots table.
    8. WebSocket manager received broadcast payload.
    9. REST API endpoints retrieve exact updated state.
"""

from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient

from app.api.application import create_app
from app.db.database import SessionLocal, init_db
from app.db.models.event import EventModel
from app.db.models.incident import IncidentModel
from app.db.models.plan import PlanModel, PlanStepModel
from app.db.models.world_state import WorldStateSnapshotModel
from app.events.factory import make_human_interrupt_event
from app.models import IncidentStatus, PlanStepStatus
from app.services import EventService, IncidentService, PlanService
from app.state.manager import state_manager
from app.ws.manager import ws_manager


@pytest.fixture
def app_client():
    init_db()
    app = create_app()
    client = TestClient(app)
    return client


@pytest.mark.anyio
async def test_inc1042_interruption_scenario():
    """Run full INC-1042 end-to-end integration flow."""
    init_db()
    db = SessionLocal()

    # Reset state manager
    await state_manager.reset()

    try:
        # Step 1: Create incident INC-1042
        inc_service = IncidentService()
        incident = await inc_service.create_incident(
            title="Payment API degradation",
            description="High latency and 5xx errors on payment gateway",
            severity="critical",
            metadata={"objective": "Identify root cause and restore service"},
            db=db,
        )
        incident_id = incident.id

        # Update status to INVESTIGATING
        await inc_service.update_status(incident_id, IncidentStatus.INVESTIGATING, db=db)

        # Step 2: Create initial plan (S1, S2, S3, S4)
        plan_service = PlanService()
        initial_steps = [
            {
                "description": "Retrieve API gateway logs",
                "tool": "retrieve_api_logs",
                "status": PlanStepStatus.COMPLETED.value,
            },
            {
                "description": "Analyze error patterns in APM",
                "tool": "analyze_error_patterns",
                "status": PlanStepStatus.COMPLETED.value,
            },
            {
                "description": "Investigate database query performance",
                "tool": "investigate_database",
                "status": PlanStepStatus.PENDING.value,
            },
            {
                "description": "Compare recent deployment diffs",
                "tool": "compare_recent_deployment",
                "status": PlanStepStatus.PENDING.value,
            },
        ]
        plan = await plan_service.create_plan(
            incident_id=incident_id,
            steps_data=initial_steps,
            rationale="Standard triage plan",
            db=db,
        )
        plan_id = plan.id

        # Step 3: Mock WebSocket manager to verify broadcast
        with patch.object(ws_manager, "broadcast", new=AsyncMock()) as mock_broadcast:
            # Step 4: Submit HUMAN_INTERRUPT event
            interrupt_evt = make_human_interrupt_event(
                text="Don't investigate the database.",
                source="operator",
                correlation_id=incident_id,
            )

            event_service = EventService()
            processed_event, updated_state = await event_service.process_event(interrupt_evt, db)

            # Step 5: Cancel S3 step as required by interrupt
            await plan_service.cancel_step(plan_id, "investigate_database", db=db)

            # Step 6: Insert replacement step S3.1 ("check_dependency_health") at index 3
            await plan_service.insert_step(
                plan_id,
                target_index=3,
                step_data={
                    "description": "Check payment vendor API dependency health",
                    "tool": "check_dependency_health",
                    "parameters": {"service": "stripe_gateway"},
                },
                db=db,
            )

            # VERIFICATION 1: Event persisted in SQLite events table
            persisted_evt = db.query(EventModel).filter_by(id=str(processed_event.id)).first()
            assert persisted_evt is not None
            assert persisted_evt.event_type == "human_interrupt"

            # VERIFICATION 2: Incident status is INTERRUPTED
            updated_inc = db.query(IncidentModel).filter_by(id=incident_id).first()
            assert updated_inc is not None
            assert updated_inc.status == IncidentStatus.INTERRUPTED.value

            # VERIFICATION 3: World state records restriction "investigate_database"
            current_ws = state_manager.current
            assert "investigate_database" in current_ws.restrictions
            assert current_ws.incident_status == IncidentStatus.INTERRUPTED

            # VERIFICATION 4 & 5: S3 CANCELLED, S4 PENDING
            mutated_plan = plan_service.get_plan(plan_id, db)
            assert mutated_plan is not None
            step_by_tool = {s.tool: s for s in mutated_plan.steps}

            assert step_by_tool["investigate_database"].status == PlanStepStatus.CANCELLED.value
            assert step_by_tool["compare_recent_deployment"].status == PlanStepStatus.PENDING.value

            # VERIFICATION 6: Inserted step S3.1 exists and is PENDING
            assert "check_dependency_health" in step_by_tool
            assert step_by_tool["check_dependency_health"].status == PlanStepStatus.PENDING.value

            # VERIFICATION 7: World State snapshot persisted in SQLite
            persisted_ws = (
                db.query(WorldStateSnapshotModel)
                .order_by(WorldStateSnapshotModel.timestamp.desc())
                .first()
            )
            assert persisted_ws is not None
            assert "investigate_database" in persisted_ws.context_json.get("restrictions", [])

            # VERIFICATION 8: WebSocket broadcast received payload
            assert mock_broadcast.called

            # VERIFICATION 9: REST API returns state from SQLite
            client = TestClient(create_app())
            res_state = client.get("/state")
            assert res_state.status_code == 200
            assert "investigate_database" in res_state.json()["restrictions"]

            res_plan = client.get(f"/plans/{plan_id}")
            assert res_plan.status_code == 200
            plan_json = res_plan.json()
            assert len(plan_json["steps"]) == 5  # S1, S2, S3 (cancelled), S3.1, S4
            assert any(s["tool"] == "investigate_database" and s["status"] == "cancelled" for s in plan_json["steps"])

    finally:
        db.close()
