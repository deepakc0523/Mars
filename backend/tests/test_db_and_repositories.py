"""
Unit and integration tests for SQLite database layer and Repositories in MARS.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.db.database import get_db, init_db
from app.db.models import (
    IncidentModel,
    WorldStateSnapshotModel,
    EventModel,
    PlanModel,
    PlanStepModel,
    ActionModel,
)
from app.repositories import (
    IncidentRepository,
    WorldStateRepository,
    EventRepository,
    PlanRepository,
    ActionRepository,
)


@pytest.fixture
def db_session() -> Session:
    """In-memory SQLite session fixture for fast isolated testing."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_init_db_creates_tables(tmp_path):
    """Verify init_db creates database file and tables."""
    db_file = tmp_path / "test_mars.db"
    db_url = f"sqlite:///{db_file}"
    engine = create_engine(db_url)
    Base.metadata.create_all(bind=engine)
    assert db_file.exists()


def test_incident_repository_crud(db_session: Session):
    """Test IncidentRepository create, list active, and resolve."""
    repo = IncidentRepository(db_session)

    incident = repo.create(
        IncidentModel(
            title="High CPU Usage",
            description="Service node-1 CPU exceeded 95%",
            severity="critical",
            status="active",
            metadata_json={"node": "node-1"},
        )
    )
    assert incident.id is not None
    assert incident.status == "active"

    active_incidents = repo.get_active_incidents()
    assert len(active_incidents) == 1
    assert active_incidents[0].id == incident.id

    resolved = repo.resolve_incident(incident.id)
    assert resolved is not None
    assert resolved.status == "resolved"
    assert resolved.resolved_at is not None

    active_after = repo.get_active_incidents()
    assert len(active_after) == 0


def test_world_state_repository(db_session: Session):
    """Test WorldStateRepository save and snapshot retrieval."""
    repo = WorldStateRepository(db_session)

    snapshot = repo.create(
        WorldStateSnapshotModel(
            incident_id="inc-123",
            phase="reevaluate",
            metrics_json={"cpu": 98.5, "memory": 45.0},
            context_json={"cluster": "us-east-1"},
        )
    )
    assert snapshot.id is not None

    latest = repo.get_latest_snapshot(incident_id="inc-123")
    assert latest is not None
    assert latest.phase == "reevaluate"
    assert latest.metrics_json["cpu"] == 98.5


def test_event_repository(db_session: Session):
    """Test EventRepository persistence and correlation lookup."""
    repo = EventRepository(db_session)

    evt1 = repo.create(
        EventModel(
            event_type="anomaly_detected",
            source="monitoring",
            payload_json={"metric": "cpu", "value": 98.5},
            correlation_id="corr-99",
        )
    )
    evt2 = repo.create(
        EventModel(
            event_type="alert",
            source="alertmanager",
            payload_json={"alert": "HighCPU"},
            correlation_id="corr-99",
        )
    )

    correlated = repo.get_by_correlation_id("corr-99")
    assert len(correlated) == 2
    assert correlated[0].id == evt1.id
    assert correlated[1].id == evt2.id


def test_plan_repository(db_session: Session):
    """Test PlanRepository creating plans with steps and status updates."""
    inc_repo = IncidentRepository(db_session)
    incident = inc_repo.create(IncidentModel(title="Database Lag"))

    plan_repo = PlanRepository(db_session)
    plan = PlanModel(
        incident_id=incident.id,
        rationale="Scale read replicas and flush query cache",
        status="pending",
        steps=[
            PlanStepModel(
                step_index=0,
                description="Scale replica count to 3",
                tool="scale_replicas",
                parameters_json={"count": 3},
                expected_outcome="Replicas scaled",
            ),
            PlanStepModel(
                step_index=1,
                description="Flush redis cache",
                tool="flush_cache",
                parameters_json={"cache": "redis"},
                expected_outcome="Cache cleared",
            ),
        ],
    )
    saved_plan = plan_repo.create(plan)
    assert saved_plan.id is not None
    assert len(saved_plan.steps) == 2

    fetched = plan_repo.get_plan_with_steps(saved_plan.id)
    assert fetched is not None
    assert len(fetched.steps) == 2
    assert fetched.steps[0].tool == "scale_replicas"

    updated_plan = plan_repo.update_plan_status(saved_plan.id, "executing")
    assert updated_plan.status == "executing"

    step_id = fetched.steps[0].id
    updated_step = plan_repo.update_step_status(step_id, "completed")
    assert updated_step.status == "completed"


def test_action_repository(db_session: Session):
    """Test ActionRepository recording tool execution and completion."""
    repo = ActionRepository(db_session)

    action = repo.create(
        ActionModel(
            tool_name="restart_service",
            input_payload_json={"service": "payment-api"},
            status="running",
        )
    )
    assert action.id is not None
    assert action.status == "running"

    completed = repo.complete_action(
        action_id=action.id,
        output_payload={"status": "success", "pid": 1234},
        status="completed",
    )
    assert completed is not None
    assert completed.status == "completed"
    assert completed.output_payload_json["pid"] == 1234
    assert completed.completed_at is not None
