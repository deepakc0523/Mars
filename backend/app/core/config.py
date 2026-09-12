"""
Configuration module for MARS backend.

All settings are sourced from environment variables (or a .env file).
Use ``get_settings()`` everywhere — it is cached after the first call.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide configuration, loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ───────────────────────────────────────────────────────────
    app_name: str = Field(default="MARS", description="Human-readable application name.")
    app_env: Literal["development", "staging", "production"] = Field(
        default="development", description="Deployment environment."
    )
    app_version: str = Field(default="0.1.0", description="Semantic version string.")

    # ── API Server ────────────────────────────────────────────────────────────
    host: str = Field(default="0.0.0.0", description="Uvicorn bind address.")
    port: int = Field(default=8000, ge=1, le=65535, description="Uvicorn port.")
    log_level: Literal["debug", "info", "warning", "error", "critical"] = Field(
        default="info", description="Log verbosity level."
    )
    reload: bool = Field(default=False, description="Enable uvicorn hot-reload (dev only).")

    # ── CORS ──────────────────────────────────────────────────────────────────
    allowed_origins: list[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        description="Allowed CORS origins.",
    )

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = Field(
        default="sqlite:///./mars.db",
        description="SQLAlchemy-compatible database URL.",
    )

    # ── AI Providers (not used in foundation phase) ───────────────────────────
    groq_api_key: str = Field(default="", description="Groq API key.")
    gemini_api_key: str = Field(default="", description="Google Gemini API key.")

    # ── Planner ───────────────────────────────────────────────────────────────
    planner_model: str = Field(default="llama-3.3-70b-versatile")
    planner_temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    planner_max_tokens: int = Field(default=2048, ge=1)

    # ── Verifier ──────────────────────────────────────────────────────────────
    verifier_model: str = Field(default="gemini-1.5-flash")
    verifier_temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    verifier_max_tokens: int = Field(default=1024, ge=1)

    # ── RAG ───────────────────────────────────────────────────────────────────
    chroma_persist_dir: str = Field(default="./chroma_db")
    embedding_model: str = Field(default="all-MiniLM-L6-v2")

    # ── Safety ────────────────────────────────────────────────────────────────
    safety_enabled: bool = Field(default=True)
    safety_strict_mode: bool = Field(default=False)

    # ── Ledger ────────────────────────────────────────────────────────────────
    ledger_db_path: str = Field(default="./mars_ledger.db")

    # ── Computed helpers ──────────────────────────────────────────────────────

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def _parse_origins(cls, v: object) -> list[str]:
        """Accept both a comma-separated string and a proper list."""
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v  # type: ignore[return-value]

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton Settings instance."""
    return Settings()
