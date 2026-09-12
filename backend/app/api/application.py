"""
FastAPI application factory for MARS.

``create_app()`` is the single entry point for constructing the FastAPI
instance.  It wires together:
  - CORS middleware
  - Lifespan (startup / shutdown hooks)
  - Exception handlers
  - Routers
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.exceptions import MARSError
from app.core.logging import configure_logging
from app.models import ErrorResponse
from app.api.routers import health

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage startup and shutdown of application resources."""
    settings = get_settings()
    configure_logging(settings.log_level)
    log.info(
        "MARS starting up | env=%s version=%s",
        settings.app_env,
        settings.app_version,
    )
    yield
    log.info("MARS shutting down.")


def create_app() -> FastAPI:
    """Construct and return the configured FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "MARS — Multi-Agent Reasoning & Adaptive Response System. "
            "Real-time incident-response agent with interruptible execution."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Exception handlers ────────────────────────────────────────────────────
    @app.exception_handler(MARSError)
    async def mars_error_handler(request: Request, exc: MARSError) -> JSONResponse:
        log.error("MARSError on %s: %s", request.url.path, exc)
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error=type(exc).__name__,
                detail=str(exc),
            ).model_dump(mode="json"),
        )

    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
        log.exception("Unhandled exception on %s", request.url.path)
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error="InternalServerError",
                detail="An unexpected error occurred.",
            ).model_dump(mode="json"),
        )

    # ── Routers ───────────────────────────────────────────────────────────────
    app.include_router(health.router)

    log.info("MARS application created with %d route(s).", len(app.routes))
    return app
