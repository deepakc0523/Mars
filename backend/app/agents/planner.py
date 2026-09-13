"""
Planner agent interface and deterministic mock implementation for MARS.
"""

from __future__ import annotations

import abc
from uuid import uuid4

from app.models import Plan, PlanStep, PlanStepStatus, ProposedPlan, WorldState


class BasePlanner(abc.ABC):
    """Abstract base interface for all Planner agents."""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Human-readable name of the planner."""

    @abc.abstractmethod
    async def plan(
        self,
        world_state: WorldState,
        available_actions: list[str] | None = None,
        previous_plan: Plan | ProposedPlan | None = None,
    ) -> ProposedPlan:
        """
        Formulate a proposed response plan based on authoritative WorldState.

        Args:
            world_state: Current point-in-time state snapshot.
            available_actions: Optional whitelist of allowable tool actions.
            previous_plan: Prior plan if this call is a replanning revision.

        Returns:
            Structured ProposedPlan.
        """


class MockPlanner(BasePlanner):
    """
    Deterministic rule-based mock planner for testing and Phase 2 orchestration.

    Guarantees reproducible plan proposals and strictly respects active restrictions
    in WorldState.
    """

    def __init__(self, *, force_restricted_tool: str | None = None) -> None:
        self._force_restricted_tool = force_restricted_tool

    @property
    def name(self) -> str:
        return "MockPlannerAgent-v1"

    async def plan(
        self,
        world_state: WorldState,
        available_actions: list[str] | None = None,
        previous_plan: Plan | ProposedPlan | None = None,
    ) -> ProposedPlan:
        """Generate deterministic proposed plan based on WorldState and active restrictions."""
        objective = (
            world_state.context.get("objective")
            or "Identify root cause and restore service"
        )
        restrictions = list(world_state.restrictions)

        steps: list[PlanStep] = []

        # Force generating a restricted tool ONLY if testing explicit verifier rejection
        if self._force_restricted_tool:
            steps.append(
                PlanStep(
                    step_id=uuid4(),
                    step_number="S1",
                    description=f"Invoking forced tool {self._force_restricted_tool}",
                    tool=self._force_restricted_tool,
                    status=PlanStepStatus.PENDING,
                )
            )
        else:
            # Standard deterministic step generation for INC-1042 scenario
            steps.append(
                PlanStep(
                    step_id=uuid4(),
                    step_number="S1",
                    description="Retrieve API gateway logs",
                    tool="retrieve_api_logs",
                    expected_outcome="API logs retrieved",
                    status=PlanStepStatus.PENDING,
                )
            )
            steps.append(
                PlanStep(
                    step_id=uuid4(),
                    step_number="S2",
                    description="Analyze error patterns in APM",
                    tool="analyze_error_patterns",
                    expected_outcome="Error signature identified",
                    status=PlanStepStatus.PENDING,
                )
            )

            # S3 Selection based on restrictions
            if "investigate_database" not in restrictions:
                steps.append(
                    PlanStep(
                        step_id=uuid4(),
                        step_number="S3",
                        description="Investigate database query performance",
                        tool="investigate_database",
                        expected_outcome="Database metrics analyzed",
                        status=PlanStepStatus.PENDING,
                    )
                )
            else:
                steps.append(
                    PlanStep(
                        step_id=uuid4(),
                        step_number="S3",
                        description="Check payment vendor API dependency health",
                        tool="check_dependency_health",
                        parameters={"service": "stripe_gateway"},
                        expected_outcome="Vendor API health status verified",
                        status=PlanStepStatus.PENDING,
                    )
                )

            steps.append(
                PlanStep(
                    step_id=uuid4(),
                    step_number="S4",
                    description="Compare recent deployment diffs",
                    tool="compare_recent_deployment",
                    expected_outcome="Deployment diff compared",
                    status=PlanStepStatus.PENDING,
                )
            )

        reasoning = (
            f"Formulated plan for incident '{world_state.incident_id}' with objective '{objective}'. "
            f"Restrictions avoided: {restrictions}"
        )

        return ProposedPlan(
            plan_id=uuid4(),
            incident_id=world_state.incident_id,
            objective=objective,
            reason=reasoning,
            steps=steps,
            restrictions_considered=restrictions,
            planner_version=self.name,
        )
