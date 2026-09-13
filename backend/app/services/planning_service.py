"""
Planning service and orchestration state machine for MARS Phase 2.
"""

from __future__ import annotations

import logging
from uuid import UUID
from sqlalchemy.orm import Session

from app.agents import BasePlanner, BaseVerifier, MockPlanner, MockVerifier
from app.db.models.plan import PlanModel
from app.events.factory import make_log_event
from app.models import AgentPhase, Plan, PlanningState, ProposedPlan, VerificationResult
from app.services.event_service import EventService
from app.services.plan_service import PlanService
from app.state.manager import state_manager

log = logging.getLogger(__name__)


class PlanningService:
    """
    Orchestrates the Planner + Verifier agent state machine with bounded replanning loops.

    Flow:
        WorldState → Planner → ProposedPlan → Verifier → VerificationResult
        If APPROVED: persist plan, emit event, attach to WorldState.
        If REJECTED: record failure, allow revision (max 3 attempts).
    """

    def __init__(
        self,
        planner: BasePlanner | None = None,
        verifier: BaseVerifier | None = None,
    ) -> None:
        self.planner = planner or MockPlanner()
        self.verifier = verifier or MockVerifier()

    async def generate_and_orchestrate_plan(
        self,
        incident_id: str,
        db: Session,
        max_attempts: int = 3,
    ) -> tuple[PlanModel | None, VerificationResult | None, PlanningState, int]:
        """
        Orchestrate plan formulation and verification loop.

        Returns:
            Tuple of (accepted_plan_model_or_none, final_verification_result, final_planning_state, attempts_used)
        """
        # Ensure incident ID set in world state
        await state_manager.set_incident(UUID(incident_id))

        current_state = PlanningState.IDLE
        previous_proposal: ProposedPlan | None = None
        last_verification_result: VerificationResult | None = None

        log.info(
            "PlanningService: starting orchestration for incident id=%s (max_attempts=%d)",
            incident_id,
            max_attempts,
        )

        for attempt in range(1, max_attempts + 1):
            # 1. State: PLANNING
            current_state = PlanningState.PLANNING
            await state_manager.transition_phase(AgentPhase.REPLAN if attempt > 1 else AgentPhase.REEVALUATE)
            ws_snapshot = state_manager.current

            log.info("PlanningService: Attempt %d/%d - state -> PLANNING", attempt, max_attempts)

            proposed_plan = await self.planner.plan(
                world_state=ws_snapshot,
                previous_plan=previous_proposal,
            )
            previous_proposal = proposed_plan

            # 2. State: VERIFYING
            current_state = PlanningState.VERIFYING
            await state_manager.transition_phase(AgentPhase.VERIFY)
            ws_snapshot = state_manager.current

            log.info("PlanningService: Attempt %d/%d - state -> VERIFYING", attempt, max_attempts)

            verification_result = await self.verifier.verify(
                world_state=ws_snapshot,
                proposed_plan=proposed_plan,
            )
            last_verification_result = verification_result

            # 3. Branch on verification result
            if verification_result.approved:
                # APPROVED
                current_state = PlanningState.APPROVED
                log.info("PlanningService: Attempt %d/%d - APPROVED", attempt, max_attempts)

                # Convert proposed steps to dicts for PlanService
                steps_data = [
                    {
                        "step_id": str(s.step_id),
                        "step_number": s.step_number,
                        "description": s.description,
                        "tool": s.tool,
                        "parameters": s.parameters,
                        "expected_outcome": s.expected_outcome,
                        "status": s.status.value,
                    }
                    for s in proposed_plan.steps
                ]

                plan_service = PlanService()
                accepted_plan = await plan_service.create_plan(
                    incident_id=incident_id,
                    steps_data=steps_data,
                    rationale=proposed_plan.reason,
                    db=db,
                )

                # Return to idle phase upon approval
                await state_manager.transition_phase(AgentPhase.IDLE)
                return accepted_plan, verification_result, PlanningState.APPROVED, attempt

            else:
                # REJECTED
                current_state = PlanningState.REJECTED
                log.warning(
                    "PlanningService: Attempt %d/%d - REJECTED issues=%s",
                    attempt,
                    max_attempts,
                    verification_result.issues,
                )

                # Record rejection log event
                rej_event = make_log_event(
                    message=f"Plan verification failed on attempt {attempt}/{max_attempts}: {verification_result.issues}",
                    level="warning",
                    source=self.verifier.name,
                    correlation_id=UUID(incident_id),
                )
                await EventService().process_event(rej_event, db)

                if attempt < max_attempts:
                    current_state = PlanningState.REPLANNING
                    log.info("PlanningService: transitioning to REPLANNING for revision")

        # Exceeded max_attempts -> FAILED
        current_state = PlanningState.FAILED
        log.error("PlanningService: orchestration FAILED after %d attempts", max_attempts)

        fail_event = make_log_event(
            message=f"Planning orchestration failed after {max_attempts} attempts.",
            level="error",
            source="PlanningService",
            correlation_id=UUID(incident_id),
        )
        await EventService().process_event(fail_event, db)
        await state_manager.transition_phase(AgentPhase.IDLE)

        return None, last_verification_result, PlanningState.FAILED, max_attempts
