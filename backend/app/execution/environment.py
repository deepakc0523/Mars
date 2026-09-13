"""
Simulated Operational Environment for MARS execution testing.
"""

from __future__ import annotations

from typing import Any


class SimulatedEnvironment:
    """
    Deterministic simulated infrastructure environment for INC-1042 scenario and execution testing.

    Tracks state for:
      - payment_api
      - api_gateway
      - database
      - payment_service
      - dependency_health
      - deployment
    """

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        """Reset environment to initial state."""
        self.error_rate: float = 18.0
        self.latency_ms: int = 850
        self.database_health: str = "healthy"
        self.gateway_health: str = "degraded"
        self.payment_service_health: str = "healthy"
        self.dependency_health: dict[str, str] = {
            "stripe_gateway": "healthy",
            "auth_provider": "healthy",
        }
        self.deployment_version: str = "v2.4.1"
        self.recent_deployments: list[dict[str, Any]] = [
            {
                "version": "v2.4.1",
                "service": "payment-api",
                "deployed_at": "2026-09-13T08:00:00Z",
                "changes": ["Updated payment route timeout settings", "Upgraded client SDK"],
            },
            {
                "version": "v2.4.0",
                "service": "payment-api",
                "deployed_at": "2026-09-10T14:30:00Z",
                "changes": ["Performance patch"],
            },
        ]

    def get_api_logs(self, limit: int = 10) -> list[dict[str, Any]]:
        """Return simulated recent API gateway log entries."""
        return [
            {
                "timestamp": "2026-09-13T12:00:01Z",
                "level": "ERROR",
                "service": "api_gateway",
                "status_code": 504,
                "latency_ms": 850,
                "message": "Gateway Timeout: POST /api/v1/payments downstream response exceeded limit",
            },
            {
                "timestamp": "2026-09-13T12:00:03Z",
                "level": "WARN",
                "service": "payment_service",
                "status_code": 500,
                "message": "Circuit breaker open for gateway endpoint",
            },
            {
                "timestamp": "2026-09-13T12:00:05Z",
                "level": "INFO",
                "service": "database",
                "message": "Query executed in 12ms",
            },
        ][:limit]

    def get_error_patterns(self) -> dict[str, Any]:
        """Return APM error pattern breakdown."""
        return {
            "primary_error": "HTTP 504 Gateway Timeout",
            "error_rate_pct": self.error_rate,
            "avg_latency_ms": self.latency_ms,
            "top_failing_endpoint": "POST /api/v1/payments",
            "affected_users_pct": 14.2,
        }

    def get_database_status(self) -> dict[str, Any]:
        """Return database health metrics."""
        return {
            "status": self.database_health,
            "cpu_utilization_pct": 24.5,
            "active_connections": 18,
            "max_connections": 200,
            "avg_query_time_ms": 11.8,
            "lock_waits": 0,
        }

    def get_deployment_diff(self) -> dict[str, Any]:
        """Return deployment comparison details."""
        return {
            "current_version": self.deployment_version,
            "previous_version": "v2.4.0",
            "deploy_time": "2026-09-13T08:00:00Z",
            "commit_sha": "a5aa200",
            "diff_summary": "1 file changed, timeout changed from 5000ms to 800ms",
            "flagged_issues": ["Timeout setting 800ms is lower than peak gateway latency 850ms"],
        }

    def get_dependencies_status(self) -> dict[str, Any]:
        """Return external dependency health status."""
        return {
            "dependencies": self.dependency_health,
            "stripe_gateway_latency_ms": 120,
            "overall_status": "healthy",
        }

    def get_gateway_status(self) -> dict[str, Any]:
        """Return payment gateway component health."""
        return {
            "status": self.gateway_health,
            "error_rate_pct": self.error_rate,
            "p99_latency_ms": self.latency_ms,
            "circuit_breaker": "open",
        }


# Global singleton instance for simulated execution runtime
simulated_environment = SimulatedEnvironment()
