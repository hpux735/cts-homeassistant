"""Fixtures for Corvallis Transit System tests."""

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest

from .const import ARRIVAL_DATA, MAP_DATA


@pytest.fixture
def mock_map_data() -> Generator[AsyncMock]:
    """Mock the CTS map endpoint."""
    with patch(
        "custom_components.corvallis_transit.config_flow.async_get_map_data",
        new=AsyncMock(return_value=MAP_DATA),
    ) as mock:
        yield mock


@pytest.fixture
def mock_arrivals() -> Generator[AsyncMock]:
    """Mock the CTS arrival endpoint."""
    with patch(
        "custom_components.corvallis_transit.coordinator.async_get_platform_arrivals",
        new=AsyncMock(return_value=ARRIVAL_DATA),
    ) as mock:
        yield mock
