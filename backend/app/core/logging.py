"""
Logging configuration for MARS.

Call ``configure_logging(level)`` once at startup. All other modules
use the standard ``logging.getLogger(__name__)`` pattern.
"""

import logging
import sys
from typing import Literal

LogLevel = Literal["debug", "info", "warning", "error", "critical"]

_LOG_FORMAT = (
    "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
)
_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"


def configure_logging(level: LogLevel = "info") -> None:
    """Configure root logger with a structured text format.

    Args:
        level: Minimum log level to emit.  One of debug / info / warning /
               error / critical.
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(numeric_level)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))

    root = logging.getLogger()
    root.setLevel(numeric_level)
    # Remove any existing handlers to avoid duplicate output.
    root.handlers.clear()
    root.addHandler(handler)

    # Suppress noisy third-party loggers in non-debug modes.
    if level != "debug":
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)

    logging.getLogger(__name__).info(
        "Logging initialised at level=%s", level.upper()
    )


def get_logger(name: str) -> logging.Logger:
    """Convenience wrapper — identical to ``logging.getLogger(name)``."""
    return logging.getLogger(name)
