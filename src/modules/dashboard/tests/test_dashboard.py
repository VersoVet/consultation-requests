"""Tests for dashboard module."""

import pytest


@pytest.mark.asyncio
async def test_dashboard_module_exists() -> None:
    """Test that dashboard module is importable."""
    from src.modules.dashboard import router

    assert router is not None
