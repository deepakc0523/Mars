"""
MARS — Multi-Agent Reasoning & Adaptive Response System
========================================================
Backend entry point.

Run with:
    uvicorn main:app --reload
or via the helper script:
    python main.py
"""

import uvicorn

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.api.application import create_app

# Build the FastAPI application.
app = create_app()

if __name__ == "__main__":
    settings = get_settings()
    configure_logging(settings.log_level)

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level,
    )
