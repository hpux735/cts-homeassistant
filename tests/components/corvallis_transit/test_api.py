"""Test the Corvallis Transit System API client."""

from unittest.mock import MagicMock

import aiohttp
import pytest

from custom_components.corvallis_transit.api import (
    CTSApiError,
    async_get_map_data,
    async_get_platform_arrivals,
)


class MockResponse:
    """Minimal async HTTP response for API tests."""

    def __init__(self, payload, error: Exception | None = None) -> None:
        self.payload = payload
        self.error = error

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args) -> None:
        return None

    def raise_for_status(self) -> None:
        if self.error:
            raise self.error

    async def json(self, content_type=None):
        return self.payload


async def test_map_data_request(hass, monkeypatch) -> None:
    """Fetch map data from the latest map endpoint."""
    response = MockResponse({"Projects": []})
    session = MagicMock()
    session.get.return_value = response
    monkeypatch.setattr(
        "custom_components.corvallis_transit.api.async_get_clientsession",
        lambda hass: session,
    )

    assert await async_get_map_data(hass) == {"Projects": []}
    assert session.get.call_args.args[0].endswith("MapData?BuildNo=0")


async def test_platform_arrivals_request(hass, monkeypatch) -> None:
    """Fetch arrivals for a platform tag."""
    response = MockResponse({"Tag": 5})
    session = MagicMock()
    session.get.return_value = response
    monkeypatch.setattr(
        "custom_components.corvallis_transit.api.async_get_clientsession",
        lambda hass: session,
    )

    assert await async_get_platform_arrivals(hass, 5) == {"Tag": 5}
    assert session.get.call_args.args[0].endswith("PlatformET?Tag=5")


@pytest.mark.parametrize(
    "response",
    [
        MockResponse({}, aiohttp.ClientError),
        MockResponse([], None),
        MockResponse({}, ValueError),
    ],
)
async def test_api_errors(hass, monkeypatch, response) -> None:
    """Reject HTTP failures and non-object responses."""
    session = MagicMock()
    session.get.return_value = response
    monkeypatch.setattr(
        "custom_components.corvallis_transit.api.async_get_clientsession",
        lambda hass: session,
    )

    with pytest.raises(CTSApiError):
        await async_get_map_data(hass)
