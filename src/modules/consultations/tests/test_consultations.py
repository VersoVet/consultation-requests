"""Tests for consultations module."""

import pytest


@pytest.mark.asyncio
async def test_consultations_module_exists() -> None:
    """Test that consultations module is importable."""
    from src.modules.consultations import router

    assert router is not None
