"""
Shared Pydantic models for MARS.

These are the canonical data shapes used across the event pipeline,
agents, API responses, and the ledger. Every layer imports from here —
never from each other.
"""

from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


# ─── Enumerations ─────────────────────────────────────────────────────────────


class EventType(str, enum.Enum):
    """All event types that can flow through the MARS pipeline."""

    # External inputs
    TEXT_INPUT = "text_input"
    SPEECH_INPUT = "speech_input"
    HUMAN_MESSAGE = "human_message"
    HUMAN_INTERRUPT = "human_interrupt"

    # System / monitoring events
    ANOMALY_DETECTED = "anomaly_detected"
    METRIC_UPDATE = "metric_update"
    ALERT = "alert"
    LOG_EVENT = "log_event"
    DEPLOYMENT_EVENT = "deployment_event"
    RECOVERY_EVENT = "recovery_event"

    # Plan events
    PLAN_CREATED = "plan_created"
    PLAN_UPDATED = "plan_updated"

    # Action events
    ACTION_STARTED = "action_started"
    ACTION_CANCELLED = "action_cancelled"
    ACTION_COMPLETED = "action_completed"

    # Lifecycle events (emitted by the agent loop itself)
    INTERRUPT = "interrupt"
    STATE_PRESERVED = "state_preserved"
    REPLAN_STARTED = "replan_started"
    REPLAN_COMPLETED = "replan_completed"
    VERIFICATION_STARTED = "verification_started"
    VERIFICATION_COMPLETED = "verification_completed"
    SAFETY_CHECK_STARTED = "safety_check_started"
    SAFETY_CHECK_COMPLETED = "safety_check_completed"
    EXECUTION_STARTED = "execution_started"
    EXECUTION_COMPLETED = "execution_completed"

    # Errors
    PIPELINE_ERROR = "pipeline_error"


class IncidentStatus(str, enum.Enum):
    """Lifecycle status of an operational incident."""

    DETECTED = "detected"
    INVESTIGATING = "investigating"
    INTERRUPTED = "interrupted"
    REPLANNING = "replanning"
    RESOLVED = "resolved"


class Severity(str, enum.Enum):
    """Severity level for alerts and anomalies."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PlanStatus(str, enum.Enum):
    """Lifecycle status of an agent plan."""

    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"
    EXECUTING = "executing"
    COMPLETED = "completed"
    ABORTED = "aborted"


class PlanStepStatus(str, enum.Enum):
    """Status of an individual step in a plan."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class AgentPhase(str, enum.Enum):
    """Current phase of the MARS agent loop (IPRRV + Execute)."""

    IDLE = "idle"
    INTERRUPT = "interrupt"
    PRESERVE = "preserve"
    REEVALUATE = "reevaluate"
    REPLAN = "replan"
    VERIFY = "verify"
    SAFETY = "safety"
    EXECUTE = "execute"


# ─── Core event model ─────────────────────────────────────────────────────────


class Event(BaseModel):
    """
    The single event type that flows through the MARS pipeline.
    """

    id: UUID = Field(default_factory=uuid4, description="Unique event identifier.")
    event_type: EventType = Field(description="Discriminates the event kind.")
    source: str = Field(description="Originator: 'user', 'system', 'agent', etc.")
    payload: dict[str, Any] = Field(
        default_factory=dict,
        description="Event-specific data. Schema depends on event_type.",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of event creation.",
    )
    correlation_id: UUID | None = Field(
        default=None,
        description="Groups related events (e.g. all events for one incident).",
    )

    model_config = {"frozen": True}


# ─── Plan models ──────────────────────────────────────────────────────────────


class PlanStep(BaseModel):
    """A single, atomic action within an agent plan."""

    step_id: UUID = Field(default_factory=uuid4)
    step_number: str = Field(default="1", description="Display index/number (e.g. 'S1', 'S3.1').")
    description: str = Field(description="Human-readable description of the action.")
    tool: str = Field(description="Tool / function name to invoke.")
    parameters: dict[str, Any] = Field(default_factory=dict)
    expected_outcome: str = Field(default="", description="Success criterion.")
    estimated_duration_seconds: int | None = Field(
        default=None, description="Optional time budget for this step."
    )
    status: PlanStepStatus = Field(default=PlanStepStatus.PENDING)


class Plan(BaseModel):
    """An ordered sequence of steps proposed by the planner agent."""

    id: UUID = Field(default_factory=uuid4)
    incident_id: UUID = Field(description="Incident this plan addresses.")
    steps: list[PlanStep] = Field(default_factory=list)
    rationale: str = Field(default="", description="Why this plan was chosen.")
    status: PlanStatus = Field(default=PlanStatus.PENDING)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


# ─── World state snapshot ─────────────────────────────────────────────────────


class WorldState(BaseModel):
    """
    A point-in-time snapshot of the system being monitored.
    """

    snapshot_id: UUID = Field(default_factory=uuid4)
    incident_id: UUID | None = Field(default=None)
    incident_status: IncidentStatus = Field(default=IncidentStatus.DETECTED)
    phase: AgentPhase = Field(default=AgentPhase.IDLE)
    active_plan_id: UUID | None = Field(default=None)
    active_action: dict[str, Any] | None = Field(
        default=None, description="Currently executing action payload if active."
    )
    restrictions: list[str] = Field(
        default_factory=list,
        description="Active constraints or prohibited tools/actions.",
    )
    metrics: dict[str, float] = Field(
        default_factory=dict,
        description="Live metric readings keyed by metric name.",
    )
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary key-value context for the current incident.",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


# ─── API response envelopes ───────────────────────────────────────────────────


class HealthResponse(BaseModel):
    """Response body for GET /health."""

    status: str = "ok"
    app_name: str
    version: str
    environment: str
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class ErrorResponse(BaseModel):
    """Standard error envelope for all 4xx / 5xx responses."""

    error: str
    detail: str | None = None
    request_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
