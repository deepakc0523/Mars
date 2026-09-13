"""
ActionController for executing plan steps against simulated environment with full event and state persistence.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4
from sqlalchemy.orm import Session

from app.db.models.action import ActionModel
from app.db.models.plan import PlanModel, PlanStepModel
from app.events.factory import (
    make_action_completed_event,
    make_action_failed_event,
    make_action_started_event,
)
from app.execution.environment import SimulatedEnvironment, simulated_environment
from app.execution.tools import tool_registry
from app.models import ExecutionContext, PlanStepStatus
from app.repositories import ActionRepository, PlanRepository
from app.services import EventService
from app.state.manager import state_manager

log = logging.getLogger(__name__)


class ActionController:
    """
    Controls step-by-step and sequential plan execution.

    Persists Action records in SQLite, updates PlanStep statuses, updates WorldState active_action,
    and emits real-time WebSocket events.
    """

    def __init__(self, env: SimulatedEnvironment | None = None) -> None:
        self.env = env or simulated_environment

    async def execute_step(
        self,
        plan_id: str,
        step: PlanStepModel,
        context: ExecutionContext,
        db: Session,
    ) -> tuple[ActionModel, bool]:
        """
        Execute a single plan step.

        Returns:
            Tuple of (ActionModel, success_boolean)
        """
        action_repo = ActionRepository(db)
        plan_repo = PlanRepository(db)

        # 1. Create ActionModel record in RUNNING state
        action_id = str(uuid4())
        action_record = ActionModel(
            id=action_id,
            plan_id=plan_id,
            step_id=step.id,
            tool_name=step.tool,
            input_payload_json=step.parameters_json or {},
            status="running",
            started_at=datetime.now(timezone.utc),
        )
        action_repo.create(action_record)

        # 2. Update PlanStep status -> IN_PROGRESS
        plan_repo.update_step_status(step.id, PlanStepStatus.IN_PROGRESS.value)

        # 3. Update ExecutionContext & WorldState active_action
        context.current_step_id = UUID(step.id)
        context.active_action_id = UUID(action_id)
        context.last_updated_at = datetime.now(timezone.utc)

        action_payload = {
            "action_id": action_id,
            "plan_id": plan_id,
            "step_id": step.id,
            "tool_name": step.tool,
            "parameters": step.parameters_json,
        }
        await state_manager.update_context(active_action=action_payload)

        # 4. Emit ACTION_STARTED event
        start_event = make_action_started_event(
            action_id=action_id,
            tool_name=step.tool,
            input_payload=step.parameters_json or {},
            plan_id=plan_id,
            step_id=step.id,
            correlation_id=context.incident_id,
        )
        event_svc = EventService()
        await event_svc.process_event(start_event, db)

        # 5. Lookup and execute tool
        tool_inst = tool_registry.get_tool(step.tool)
        try:
            log.info("ActionController: executing tool '%s' for step id=%s", step.tool, step.id)
            output = tool_inst.execute(self.env, step.parameters_json or {})

            # Execution Success
            action_record = action_repo.complete_action(
                action_id=action_id,
                output_payload=output,
                status="completed",
            )
            plan_repo.update_step_status(step.id, PlanStepStatus.COMPLETED.value)

            context.completed_steps.append(step.id)
            context.active_action_id = None

            # Emit ACTION_COMPLETED event
            completed_evt = make_action_completed_event(
                action_id=action_id,
                tool_name=step.tool,
                output_payload=output,
                plan_id=plan_id,
                step_id=step.id,
                correlation_id=context.incident_id,
            )
            await event_svc.process_event(completed_evt, db)
            return action_record, True

        except Exception as exc:
            # Execution Failure
            err_msg = str(exc)
            log.error("ActionController: tool '%s' failed: %s", step.tool, err_msg)

            action_record = action_repo.complete_action(
                action_id=action_id,
                output_payload={"error": err_msg},
                status="failed",
                error_message=err_msg,
            )
            plan_repo.update_step_status(step.id, PlanStepStatus.FAILED.value)

            context.failed_steps.append(step.id)
            context.active_action_id = None

            # Emit ACTION_FAILED event
            fail_evt = make_action_failed_event(
                action_id=action_id,
                tool_name=step.tool,
                error_message=err_msg,
                plan_id=plan_id,
                step_id=step.id,
                correlation_id=context.incident_id,
            )
            await event_svc.process_event(fail_evt, db)
            return action_record, False

    async def execute_plan(self, plan_id: str, db: Session) -> ExecutionContext:
        """
        Execute all pending steps of a plan sequentially.

        Stops execution cleanly if any step fails, preserving historical steps.
        """
        plan_repo = PlanRepository(db)
        plan = plan_repo.get_plan_with_steps(plan_id)
        if not plan:
            raise ValueError(f"Plan '{plan_id}' not found.")

        sorted_steps = sorted(plan.steps, key=lambda s: s.step_index)
        incident_uuid = UUID(plan.incident_id) if plan.incident_id else None

        pending_step_ids = [s.id for s in sorted_steps if s.status == PlanStepStatus.PENDING.value]
        completed_step_ids = [s.id for s in sorted_steps if s.status == PlanStepStatus.COMPLETED.value]
        failed_step_ids = [s.id for s in sorted_steps if s.status == PlanStepStatus.FAILED.value]

        context = ExecutionContext(
            incident_id=incident_uuid,
            plan_id=UUID(plan_id),
            completed_steps=completed_step_ids,
            failed_steps=failed_step_ids,
            pending_steps=pending_step_ids,
            status="running",
        )

        log.info(
            "ActionController: starting execution for plan id=%s (%d steps pending)",
            plan_id,
            len(pending_step_ids),
        )

        for step in sorted_steps:
            if step.status != PlanStepStatus.PENDING.value:
                continue

            action_record, success = await self.execute_step(plan_id, step, context, db)

            if not success:
                log.warning(
                    "ActionController: plan execution HALTED on step id=%s tool=%s due to failure",
                    step.id,
                    step.tool,
                )
                context.status = "failed"
                context.last_updated_at = datetime.now(timezone.utc)
                plan.status = "aborted"
                db.commit()
                return context

        context.status = "completed"
        context.last_updated_at = datetime.now(timezone.utc)
        plan.status = "completed"
        db.commit()

        log.info("ActionController: plan id=%s completed successfully", plan_id)
        return context
