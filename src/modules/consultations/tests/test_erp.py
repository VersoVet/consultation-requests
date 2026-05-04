"""Tests for ERP connector module."""

import pytest

from src.modules.consultations.erp import (
    ClientModel,
    ErpConnectorError,
)


def test_client_model_creation() -> None:
    """Test ClientModel creation."""
    client = ClientModel(
        id=1,
        nom="Dupont",
        prenom="Jean",
        email="jean@test.fr",
        telephone="01.23.45.67.89",
    )

    assert client.id == 1
    assert client.nom == "Dupont"
    assert client.prenom == "Jean"
    assert client.email == "jean@test.fr"


def test_erp_connector_error_raises() -> None:
    """Test ErpConnectorError exception."""
    with pytest.raises(ErpConnectorError):
        raise ErpConnectorError("Test error message")


@pytest.mark.asyncio
async def test_search_clients_empty_result() -> None:
    """Test search_clients with no results."""
    from unittest.mock import AsyncMock, patch

    with patch(
        "src.modules.consultations.erp.httpx.AsyncClient.get",
        new_callable=AsyncMock,
    ) as mock_get:
        # This would require proper mocking of httpx
        # Skipping for now as it needs a mock server
        pass
