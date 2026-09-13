/**
 * Canonical TypeScript types for MARS frontend.
 *
 * These mirror the Pydantic models in backend/app/models/models.py.
 */

// ── Enumerations ──────────────────────────────────────────────────────────────

export type EventType =
  | "text_input"
  | "speech_input"
  | "human_message"
  | "human_interrupt"
  | "anomaly_detected"
  | "metric_update"
  | "alert"
  | "log_event"
  | "deployment_event"
  | "recovery_event"
  | "plan_created"
  | "plan_updated"
  | "action_started"
  | "action_cancelled"
  | "action_completed"
  | "interrupt"
  | "state_preserved"
  | "replan_started"
  | "replan_completed"
  | "verification_started"
  | "verification_completed"
  | "safety_check_started"
  | "safety_check_completed"
  | "execution_started"
  | "execution_completed"
  | "pipeline_error";

export type IncidentStatus =
  | "detected"
  | "investigating"
  | "interrupted"
  | "replanning"
  | "resolved";

export type Severity = "low" | "medium" | "high" | "critical";

export type PlanStatus =
  | "pending"
  | "verified"
  | "rejected"
  | "executing"
  | "completed"
  | "aborted";

export type PlanStepStatus =
  | "pending"
  | "in_progress"
  | "completed"
  | "cancelled"
  | "failed";

export type PlanningState =
  | "idle"
  | "planning"
  | "verifying"
  | "approved"
  | "rejected"
  | "replanning"
  | "failed";

export type AgentPhase =
  | "idle"
  | "interrupt"
  | "preserve"
  | "reevaluate"
  | "replan"
  | "verify"
  | "safety"
  | "execute";

// ── Core models ───────────────────────────────────────────────────────────────

export interface MarsEvent {
  id: string;
  event_type: EventType;
  source: string;
  payload: Record<string, unknown>;
  timestamp: string; // ISO-8601 UTC
  correlation_id: string | null;
}

export interface PlanStep {
  step_id: string;
  step_number?: string;
  description: string;
  tool: string;
  parameters: Record<string, unknown>;
  expected_outcome: string;
  estimated_duration_seconds?: number | null;
  status: PlanStepStatus;
}

export interface Plan {
  id: string;
  incident_id: string;
  steps: PlanStep[];
  rationale: string;
  status: PlanStatus;
  created_at: string;
  updated_at: string;
}

export interface ProposedPlan {
  plan_id: string;
  incident_id: string | null;
  objective: string;
  reason: string;
  steps: PlanStep[];
  restrictions_considered: string[];
  planner_version: string;
  created_at: string;
}

export interface VerificationResult {
  approved: boolean;
  risk_level: string;
  issues: string[];
  warnings: string[];
  checked_restrictions: string[];
  verifier_version: string;
  timestamp: string;
}

export interface WorldState {
  snapshot_id: string;
  incident_id: string | null;
  incident_status: IncidentStatus;
  phase: AgentPhase;
  active_plan_id: string | null;
  active_action: Record<string, unknown> | null;
  restrictions: string[];
  metrics: Record<string, number>;
  context: Record<string, unknown>;
  timestamp: string;
}

// ── API response envelopes ────────────────────────────────────────────────────

export interface GeneratePlanResponse {
  status: "approved" | "failed";
  planning_state: PlanningState;
  attempts: number;
  plan: Plan | null;
  verification_result: VerificationResult | null;
}

export interface HealthResponse {
  status: string;
  app_name: string;
  version: string;
  environment: string;
  timestamp: string;
}

export interface ErrorResponse {
  error: string;
  detail: string | null;
  request_id: string;
  timestamp: string;
}

// ── WebSocket message envelopes ───────────────────────────────────────────────

export interface WsMessage<T = unknown> {
  type: string;
  event?: MarsEvent;
  state?: WorldState;
  payload?: T;
  timestamp?: string;
}

export type WsEventMessage = WsMessage<MarsEvent>;
export type WsStateMessage = WsMessage<WorldState>;
