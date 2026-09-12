/**
 * Canonical TypeScript types for MARS frontend.
 *
 * These mirror the Pydantic models in backend/app/models/models.py.
 * Keep these in sync when the backend models change.
 */

// ── Enumerations ──────────────────────────────────────────────────────────────

export type EventType =
  | "text_input"
  | "speech_input"
  | "anomaly_detected"
  | "metric_update"
  | "alert"
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

export type Severity = "low" | "medium" | "high" | "critical";

export type PlanStatus =
  | "pending"
  | "verified"
  | "rejected"
  | "executing"
  | "completed"
  | "aborted";

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
  description: string;
  tool: string;
  parameters: Record<string, unknown>;
  expected_outcome: string;
  estimated_duration_seconds: number | null;
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

export interface WorldState {
  snapshot_id: string;
  incident_id: string | null;
  phase: AgentPhase;
  active_plan_id: string | null;
  metrics: Record<string, number>;
  context: Record<string, unknown>;
  timestamp: string;
}

// ── API response envelopes ────────────────────────────────────────────────────

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

/**
 * All messages sent from the MARS backend over WebSocket are wrapped in this
 * envelope. The ``type`` field discriminates the message shape.
 */
export interface WsMessage<T = unknown> {
  type: string;
  payload: T;
  timestamp: string;
}

export type WsEventMessage = WsMessage<MarsEvent>;
export type WsStateMessage = WsMessage<WorldState>;
