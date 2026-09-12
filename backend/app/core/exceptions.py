"""
Domain-level exceptions for MARS.

Raise these from service / agent layers; the FastAPI exception handlers
in ``app.api.application`` translate them to appropriate HTTP responses.
"""


class MARSError(Exception):
    """Base exception for all MARS-specific errors."""


class ConfigurationError(MARSError):
    """Raised when required configuration is missing or invalid."""


class StateError(MARSError):
    """Raised when a state transition is illegal."""


class PlanningError(MARSError):
    """Raised when the planner agent fails to produce a valid plan."""


class VerificationError(MARSError):
    """Raised when the verifier agent rejects a plan."""


class SafetyGateError(MARSError):
    """Raised when the safety gate blocks plan execution."""


class LedgerError(MARSError):
    """Raised on ledger integrity failures."""


class EventError(MARSError):
    """Raised when an event cannot be processed."""
