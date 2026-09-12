"""
Tests for configuration module.
"""

from __future__ import annotations

import pytest

from app.core.config import Settings, get_settings


class TestSettings:
    def test_defaults_are_valid(self) -> None:
        s = Settings()
        assert s.app_name == "MARS"
        assert s.app_env == "development"
        assert s.port == 8000
        assert s.log_level == "info"

    def test_allowed_origins_parsed_from_string(self) -> None:
        s = Settings(allowed_origins="http://a.com,http://b.com")  # type: ignore[call-arg]
        assert s.allowed_origins == ["http://a.com", "http://b.com"]

    def test_is_development(self) -> None:
        s = Settings(app_env="development")  # type: ignore[call-arg]
        assert s.is_development is True
        assert s.is_production is False

    def test_is_production(self) -> None:
        s = Settings(app_env="production")  # type: ignore[call-arg]
        assert s.is_production is True
        assert s.is_development is False

    def test_get_settings_returns_singleton(self) -> None:
        a = get_settings()
        b = get_settings()
        assert a is b
