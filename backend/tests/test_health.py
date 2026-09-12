"""
Tests for GET /health endpoint and the application factory.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.application import create_app


@pytest.fixture(scope="module")
def client() -> TestClient:
    app = create_app()
    return TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_200(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_response_shape(self, client: TestClient) -> None:
        data = client.get("/health").json()
        assert data["status"] == "ok"
        assert "app_name" in data
        assert "version" in data
        assert "environment" in data
        assert "timestamp" in data

    def test_health_app_name(self, client: TestClient) -> None:
        data = client.get("/health").json()
        assert data["app_name"] == "MARS"

    def test_docs_available(self, client: TestClient) -> None:
        response = client.get("/docs")
        assert response.status_code == 200

    def test_openapi_schema(self, client: TestClient) -> None:
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "openapi" in schema
        assert "paths" in schema
        assert "/health" in schema["paths"]
