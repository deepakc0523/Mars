"""
Pytest configuration and fixtures.
"""

import pytest


@pytest.fixture
def anyio_backend():
    """Limit anyio test runner to asyncio backend."""
    return "asyncio"
