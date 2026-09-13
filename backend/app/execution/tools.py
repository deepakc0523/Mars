"""
Tool abstractions and deterministic simulated tools for MARS execution engine.
"""

from __future__ import annotations

import abc
import logging
from typing import Any

from app.execution.environment import SimulatedEnvironment, simulated_environment

log = logging.getLogger(__name__)


class BaseTool(abc.ABC):
    """Abstract base class for all MARS execution tools."""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Unique, stable tool identifier."""

    @abc.abstractmethod
    def execute(
        self,
        env: SimulatedEnvironment,
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Execute tool action against the simulated environment.

        Args:
            env: Simulated environment state.
            parameters: Input parameters for the tool.

        Returns:
            Structured output result dict.
        """


class RetrieveApiLogsTool(BaseTool):
    """Tool retrieving recent API logs."""

    @property
    def name(self) -> str:
        return "retrieve_api_logs"

    def execute(self, env: SimulatedEnvironment, parameters: dict[str, Any]) -> dict[str, Any]:
        limit = parameters.get("limit", 10)
        logs = env.get_api_logs(limit=limit)
        return {
            "status": "success",
            "log_count": len(logs),
            "logs": logs,
        }


class AnalyzeErrorPatternsTool(BaseTool):
    """Tool analyzing APM error metrics."""

    @property
    def name(self) -> str:
        return "analyze_error_patterns"

    def execute(self, env: SimulatedEnvironment, parameters: dict[str, Any]) -> dict[str, Any]:
        analysis = env.get_error_patterns()
        return {
            "status": "success",
            "analysis": analysis,
        }


class InvestigateDatabaseTool(BaseTool):
    """Tool checking database performance and query health."""

    @property
    def name(self) -> str:
        return "investigate_database"

    def execute(self, env: SimulatedEnvironment, parameters: dict[str, Any]) -> dict[str, Any]:
        db_metrics = env.get_database_status()
        return {
            "status": "success",
            "database_metrics": db_metrics,
        }


class CompareRecentDeploymentTool(BaseTool):
    """Tool inspecting recent deployment changelogs and diffs."""

    @property
    def name(self) -> str:
        return "compare_recent_deployment"

    def execute(self, env: SimulatedEnvironment, parameters: dict[str, Any]) -> dict[str, Any]:
        diff_info = env.get_deployment_diff()
        return {
            "status": "success",
            "deployment_diff": diff_info,
        }


class CheckDependencyHealthTool(BaseTool):
    """Tool checking health of external third-party API dependencies."""

    @property
    def name(self) -> str:
        return "check_dependency_health"

    def execute(self, env: SimulatedEnvironment, parameters: dict[str, Any]) -> dict[str, Any]:
        dep_info = env.get_dependencies_status()
        return {
            "status": "success",
            "dependency_health": dep_info,
        }


class CheckPaymentGatewayTool(BaseTool):
    """Tool checking payment gateway component health."""

    @property
    def name(self) -> str:
        return "check_payment_gateway"

    def execute(self, env: SimulatedEnvironment, parameters: dict[str, Any]) -> dict[str, Any]:
        gw_info = env.get_gateway_status()
        return {
            "status": "success",
            "gateway_status": gw_info,
        }


class FailingMockTool(BaseTool):
    """Test tool that explicitly raises an exception to test failure handling."""

    @property
    def name(self) -> str:
        return "failing_mock_tool"

    def execute(self, env: SimulatedEnvironment, parameters: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("Simulated tool execution failure: Service connection timed out.")


class ToolRegistry:
    """Registry mapping tool names to executable BaseTool instances."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}
        # Register standard tools
        for tool in [
            RetrieveApiLogsTool(),
            AnalyzeErrorPatternsTool(),
            InvestigateDatabaseTool(),
            CompareRecentDeploymentTool(),
            CheckDependencyHealthTool(),
            CheckPaymentGatewayTool(),
            FailingMockTool(),
        ]:
            self.register(tool)

    def register(self, tool: BaseTool) -> None:
        """Register a tool instance."""
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> BaseTool:
        """Lookup tool by name. Returns fallback generic tool if unknown."""
        if name in self._tools:
            return self._tools[name]
        return GenericFallbackTool(name)


class GenericFallbackTool(BaseTool):
    """Fallback tool for unmapped tool names."""

    def __init__(self, tool_name: str) -> None:
        self._name = tool_name

    @property
    def name(self) -> str:
        return self._name

    def execute(self, env: SimulatedEnvironment, parameters: dict[str, Any]) -> dict[str, Any]:
        return {
            "status": "success",
            "tool": self._name,
            "result": f"Executed tool '{self._name}' with params {parameters}",
        }


# Global tool registry singleton
tool_registry = ToolRegistry()
