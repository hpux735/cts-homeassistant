"""HTTP client for the public Corvallis Transit System API."""

from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import API_BASE, MAP_BUILD_NO, REQUEST_TIMEOUT_SECONDS


class CTSApiError(Exception):
    """Raised when the CTS API cannot provide valid data."""


async def _get_json(hass: HomeAssistant, path: str) -> dict[str, Any]:
    """Fetch a JSON response from CTS."""
    session = async_get_clientsession(hass)
    try:
        async with session.get(
            f"{API_BASE}/{path}",
            timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_SECONDS),
        ) as response:
            response.raise_for_status()
            data = await response.json(content_type=None)
    except (aiohttp.ClientError, TimeoutError, ValueError) as err:
        raise CTSApiError from err

    if not isinstance(data, dict):
        raise CTSApiError("CTS API returned an unexpected response")
    return data


async def async_get_map_data(hass: HomeAssistant) -> dict[str, Any]:
    """Fetch agencies, routes, stops, and route geometry."""
    return await _get_json(hass, f"MapData?BuildNo={MAP_BUILD_NO}")


async def async_get_platform_arrivals(
    hass: HomeAssistant, platform_tag: int
) -> dict[str, Any]:
    """Fetch live arrivals for a platform or station."""
    return await _get_json(hass, f"PlatformET?Tag={platform_tag}")
