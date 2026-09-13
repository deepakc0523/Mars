"""
Comprehensive unit and integration tests for Phase 1 Continuation.
"""

import pytest
from fastapi.testclient import TestClient

from app.api.application import create_app
from app.db.database import SessionLocal, init_db
from app.events.factory import (
    make_deployment_event,
    make_human_interrupt_event,
    make_human_message_event,
    make_log_event,
    make_metric_update_event,
    make_recovery_event,
)
from app.models import EventType, IncidentStatus, PlanStepStatus
from app.services import EventService, IncidentService, PlanService
from app.state.lifecycle import InvalidLifecycleTransitionError, validate_lifecycle_transition
from app.state.manager import state_manager


@pytest.fixture
def client():
    init_db()
    app = create_app()
    return TestClient(app)


@pytest.mark.anyio
async def test_event_state_transitions():
    """Test deterministic state transitions for event types."""
    init_db()
    db = SessionLocal()
    await state_manager.reset()

    try:
        svc = EventService()

        # 1. HUMAN_MESSAGE
        msg_evt = make_human_message_event("Checking service health")
        _, s1 = await svc.process_event(msg_evt, db)
        assert s1.context["last_human_message"] == "Checking service health"

        # 2. METRIC_UPDATE
        metric_evt = make_metric_update_event({"cpu_usage": 92.4})
        _, s2 = await svc.process_event(metric_evt, db)
        assert s2.metrics["cpu_usage"] == 92.4

        # 3. DEPLOYMENT_EVENT
        dep_evt = make_deployment_event("auth-service", "v2.1.0")
        _, s3 = await svc.process_event(dep_evt, db)
        assert len(s3.context["deployments"]) == 1
        assert s3.context["deployments"][0]["version"] == "v2.1.0"

        # 4. RECOVERY_EVENT
        rec_evt = make_recovery_event("auth-service")
        _, s4 = await svc.process_event(rec_evt, db)
        assert len(s4.context["recoveries"]) == 1

        # 5. LOG_EVENT
        log_evt = make_log_event("OOM error detected on node 4")
        _, s5 = await svc.process_event(log_evt, db)
        assert len(s5.context["logs"]) == 1

    finally:
        db.close()


def test_incident_lifecycle_terminal_resolved_rules():
    """Test strict incident lifecycle rules including RESOLVED terminal state enforcement."""
    # DETECTED -> INVESTIGATING -> RESOLVED
    assert validate_lifecycle_transition(IncidentStatus.DETECTED, IncidentStatus.INVESTIGATING) == IncidentStatus.INVESTIGATING
    assert validate_lifecycle_transition(IncidentStatus.INVESTIGATING, IncidentStatus.RESOLVED) == IncidentStatus.RESOLVED

    # Normal status updates out of RESOLVED must fail
    with pytest.raises(InvalidLifecycleTransitionError):
        validate_lifecycle_transition(IncidentStatus.RESOLVED, IncidentStatus.INVESTIGATING)

    with pytest.raises(InvalidLifecycleTransitionError):
        validate_lifecycle_transition(IncidentStatus.RESOLVED, IncidentStatus.REPLANNING)

    with pytest.raises(InvalidLifecycleTransitionError):
        validate_lifecycle_transition(IncidentStatus.RESOLVED, IncidentStatus.DETECTED, is_reopen_event=False)

    # RESOLVED -> DETECTED is allowed ONLY if is_reopen_event=True
    assert validate_lifecycle_transition(IncidentStatus.RESOLVED, IncidentStatus.DETECTED, is_reopen_event=True) == IncidentStatus.DETECTED


@pytest.mark.anyio
async def test_plan_mutation_preserves_history():
    """Test plan step addition, insertion, cancellation without deletion."""
    init_db()
    db = SessionLocal()
    await state_manager.reset()

    try:
        inc_svc = IncidentService()
        inc = await inc_svc.create_incident(title="Network Latency", db=db)

        plan_svc = PlanService()
        plan = await plan_svc.create_plan(
            incident_id=inc.id,
            steps_data=[
                {"tool": "ping_router", "description": "Ping main router", "status": "completed"},
                {"tool": "check_dns", "description": "Check DNS resolution", "status": "pending"},
            ],
            db=db,
        )

        # Cancel step check_dns
        mutated1 = await plan_svc.cancel_step(plan.id, "check_dns", db=db)
        assert len(mutated1.steps) == 2
        dns_step = [s for s in mutated1.steps if s.tool == "check_dns"][0]
        assert dns_step.status == PlanStepStatus.CANCELLED.value

        # Insert new step S1.1
        mutated2 = await plan_svc.insert_step(
            plan.id,
            target_index=1,
            step_data={"tool": "traceroute", "description": "Run traceroute to gateway"},
            db=db,
        )
        assert len(mutated2.steps) == 3

    finally:
        db.close()


def test_rest_api_endpoints(client: TestClient):
    """Test REST endpoints for events, incidents, state, and plans."""
    # 1. POST /events
    evt_res = client.post(
        "/events",
        json={
            "event_type": "human_message",
            "source": "operator",
            "payload": {"text": "Hello MARS"},
        },
    )
    assert evt_res.status_code == 201
    assert evt_res.json()["status"] == "processed"

    # 2. GET /events/history
    hist_res = client.get("/events/history")
    assert hist_res.status_code == 200
    assert len(hist_res.json()) >= 1

    # 3. POST /incidents
    inc_res = client.post("/incidents", json={"title": "High Disk Usage", "severity": "high"})
    assert inc_res.status_code == 201
    inc_id = inc_res.json()["id"]

    # 4. GET /incidents/{id}
    inc_detail = client.get(f"/incidents/{inc_id}")
    assert inc_detail.status_code == 200
    assert inc_detail.json()["title"] == "High Disk Usage"

    # 5. PATCH /incidents/{id}/status
    status_res = client.patch(f"/incidents/{inc_id}/status", json={"status": "investigating"})
    assert status_res.status_code == 200
    assert status_res.json()["status"] == "investigating"

    # 6. GET /state & PATCH /state
    state_res = client.get("/state")
    assert state_res.status_code == 200

    patch_state_res = client.patch("/state", json={"context": {"region": "us-west-2"}})
    assert patch_state_res.status_code == 200
    assert patch_state_res.json()["context"]["region"] == "us-west-2"

    # 7. POST /plans & GET /plans/{id}
    plan_res = client.post(
        "/plans",
        json={
            "incident_id": inc_id,
            "rationale": "Clear log files",
            "steps": [{"description": "Clean /var/log", "tool": "clean_logs"}],
        },
    )
    assert plan_res.status_code == 201
    plan_id = plan_res.json()["id"]

    get_plan_res = client.get(f"/plans/{plan_id}")
    assert get_plan_res.status_code == 200
    assert len(get_plan_res.json()["steps"]) == 1


def test_websocket_connection(client: TestClient):
    """Test live WebSocket connection endpoint."""
    with client.websocket_connect("/events/live") as websocket:
        websocket.send_text("ping")
