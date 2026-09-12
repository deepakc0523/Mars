"""
Health router — GET /health

Returns a lightweight status response so load balancers, CI pipelines,
and developers can confirm the service is running.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter

from app.core.config import get_settings
from app.models import HealthResponse

log = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description=(
        "Returns the current health status of the MARS backend. "
        "A 200 response indicates the service is running and configured."
    ),
)
async def health_check() -> HealthResponse:
    """Return service health status."""
    settings = get_settings()
    log.debug("Health check requested.")
    return HealthResponse(
        status="ok",
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
    )
