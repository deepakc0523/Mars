"""
End-to-End Core Integration Scenario Test for MARS Phase 2 — INC-1042.

Scenario:
  Incident: INC-1042
  Objective: Identify root cause and restore service
  Initial Restrictions: None

  Step 1: PlanningService generates PLAN-001
          Planner generates: S1 retrieve_api_logs, S2 analyze_error_patterns, S3 investigate_database, S4 compare_recent_deployment
          Verifier: APPROVED
          Persist PLAN-001.

  Step 2: INTERRUPTION
          Submit HUMAN_INTERRUPT ("Don't investigate the database.")
          Phase 1 processes event -> WorldState.restrictions = ["investigate_database"]
          Incident status = INTERRUPTED

  Step 3: REPLANNING
          PlanningService generates PLAN-002 reading updated WorldState
          Planner generates: S1 retrieve_api_logs, S2 analyze_error_patterns, S3 check_dependency_health, S4 compare_recent_deployment
          Verifier: APPROVED
          Persist PLAN-002.

  Step 4: ASSERTIONS
          - PLAN-001 preserved in history.
          - PLAN-002 active in WorldState.
          - investigate_database absent from PLAN-002.
          - check_dependency_health present in PLAN-002.
          - WorldState points to PLAN-002.
          - restriction remains persisted.
          - PLAN_CREATED / PLAN_UPDATED events persisted.
          - Planning state machine reaches APPROVED.
          - No infinite planner loop occurs.
"""

from uuid import UUID
import pytest

from app.db.database import SessionLocal, init_db
from app.db.models.event import EventModel
from app.db.models.plan import PlanModel
from app.events.factory import make_human_interrupt_event
from app.models import IncidentStatus, PlanningState
from app.services import EventService, IncidentService, PlanningService
from app.state.manager import state_manager


@pytest.mark.anyio
async def test_inc1042_phase2_replanning_scenario():
    """Execute complete Phase 2 INC-1042 interruption and replanning orchestration flow."""
    init_db()
    db = SessionLocal()
    await state_manager.reset()

    try:
        # Step 1: Create incident INC-1042
        inc_svc = IncidentService()
        incident = await inc_svc.create_incident(
            title="Payment API degradation",
            description="High latency and 5xx errors on payment gateway",
            severity="critical",
            metadata={"objective": "Identify root cause and restore service"},
            db=db,
        )
        incident_id = incident.id

        # Update status to INVESTIGATING
        await inc_svc.update_status(incident_id, IncidentStatus.INVESTIGATING, db=db)

        # Step 2: Initial Plan Generation (PLAN-001)
        planning_svc = PlanningService()
        plan1, ver_result1, state1, attempts1 = (
            await planning_svc.generate_and_orchestrate_plan(incident_id, db=db)
        )

        assert state1 == PlanningState.APPROVED
        assert attempts1 == 1
        assert plan1 is not None
        plan1_id = plan1.id

        # Verify PLAN-001 contains investigate_database
        plan1_tools = [s.tool for s in plan1.steps]
        assert "investigate_database" in plan1_tools
        assert "check_dependency_health" not in plan1_tools

        # Step 3: Human Interruption Event ("Don't investigate the database.")
        interrupt_evt = make_human_interrupt_event(
            text="Don't investigate the database.",
            source="operator",
            correlation_id=UUID(incident_id),
        )

        event_svc = EventService()
        await event_svc.process_event(interrupt_evt, db=db)

        # Verify restriction applied to WorldState
        ws_after_interrupt = state_manager.current
        assert "investigate_database" in ws_after_interrupt.restrictions
        assert ws_after_interrupt.incident_status == IncidentStatus.INTERRUPTED

        # Step 4: Replanning Orchestration (PLAN-002)
        plan2, ver_result2, state2, attempts2 = (
            await planning_svc.generate_and_orchestrate_plan(incident_id, db=db)
        )

        assert state2 == PlanningState.APPROVED
        assert attempts2 == 1
        assert plan2 is not None
        plan2_id = plan2.id
        assert plan2_id != plan1_id

        # Step 5: Assertions & Validations
        plan2_tools = [s.tool for s in plan2.steps]
        assert "investigate_database" not in plan2_tools
        assert "check_dependency_health" in plan2_tools

        # Assertion: PLAN-001 preserved in history
        all_plans = db.query(PlanModel).filter_by(incident_id=incident_id).all()
        assert len(all_plans) >= 2
        plan_ids = [p.id for p in all_plans]
        assert plan1_id in plan_ids
        assert plan2_id in plan_ids

        # Assertion: WorldState points to PLAN-002
        current_ws = state_manager.current
        assert str(current_ws.active_plan_id) == str(plan2_id)

        # Assertion: Restriction remains persisted
        assert "investigate_database" in current_ws.restrictions

        # Assertion: PLAN_CREATED / PLAN_UPDATED events persisted
        plan_events = (
            db.query(EventModel)
            .filter(EventModel.event_type.in_(["plan_created", "plan_updated"]))
            .all()
        )
        assert len(plan_events) >= 2

    finally:
        db.close()
