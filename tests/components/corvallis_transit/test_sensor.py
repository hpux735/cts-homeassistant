"""Test Corvallis Transit System sensors."""

from unittest.mock import AsyncMock

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.corvallis_transit.api import CTSApiError
from custom_components.corvallis_transit.const import DOMAIN
from custom_components.corvallis_transit.coordinator import CTSDataUpdateCoordinator

from .const import CONFIG, UNIQUE_ID
from .const import DOMAIN as TEST_DOMAIN


async def _setup_entry(hass: HomeAssistant, data: dict) -> MockConfigEntry:
    """Add and set up a CTS config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=data,
        unique_id=f"{data['project']}_{data['route']}_{data['platform_tag']}",
        title="CTS test",
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_live_arrivals(hass: HomeAssistant, mock_arrivals: AsyncMock) -> None:
    """Expose the earliest live arrival and all upcoming minutes."""
    entry = await _setup_entry(hass, CONFIG)
    entity_id = er.async_get(hass).async_get_entity_id(
        Platform.SENSOR, TEST_DOMAIN, UNIQUE_ID
    )
    assert entity_id is not None
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state not in ("unknown", "unavailable")
    assert state.attributes["upcoming"] == "4, 18"
    assert state.attributes["destination"] == "Downtown Transit Center"
    assert entry.state is ConfigEntryState.LOADED
    assert mock_arrivals.await_count == 1


async def test_malformed_and_empty_arrivals(
    hass: HomeAssistant, mock_arrivals: AsyncMock
) -> None:
    """Malformed nested data should make the sensor unknown, not crash."""
    mock_arrivals.return_value = {
        "Created": "9:15 AM",
        "Projects": [
            {
                "Tag": 1,
                "Routes": [
                    {
                        "No": "2",
                        "Name": "9th st/hospital",
                        "Destinations": [
                            {
                                "Name": "Downtown",
                                "Trips": [{"ET": "bad"}, {"ET": True}],
                            }
                        ],
                    }
                ],
            }
        ],
    }
    await _setup_entry(hass, CONFIG)
    entity_id = er.async_get(hass).async_get_entity_id(
        Platform.SENSOR, TEST_DOMAIN, UNIQUE_ID
    )
    assert entity_id is not None
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "unknown"


@pytest.mark.parametrize(
    "payload",
    [
        [],
        {"Projects": {}},
        {"Projects": [None]},
        {"Projects": [{"Tag": 1, "Routes": {}}]},
        {"Projects": [{"Tag": 1, "Routes": [None]}]},
        {
            "Projects": [
                {
                    "Tag": 1,
                    "Routes": [
                        {
                            "No": "2",
                            "Name": "9th st/hospital",
                            "Destinations": {},
                        }
                    ],
                }
            ]
        },
        {
            "Projects": [
                {
                    "Tag": 1,
                    "Routes": [
                        {
                            "No": "2",
                            "Name": "9th st/hospital",
                            "Destinations": [{"Name": "Downtown", "Trips": {}}],
                        }
                    ],
                }
            ]
        },
    ],
)
async def test_invalid_nested_arrivals(
    hass: HomeAssistant, mock_arrivals: AsyncMock, payload: dict
) -> None:
    """Ignore invalid nested payload containers without callback errors."""
    mock_arrivals.return_value = payload
    await _setup_entry(hass, CONFIG)
    entity_id = er.async_get(hass).async_get_entity_id(
        Platform.SENSOR, TEST_DOMAIN, UNIQUE_ID
    )
    assert entity_id is not None
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "unknown"


async def test_scheduled_only_arrivals(
    hass: HomeAssistant, mock_arrivals: AsyncMock
) -> None:
    """Expose scheduled arrivals without treating them as live ETAs."""
    mock_arrivals.return_value = {
        "Created": "9:15 AM",
        "Projects": [
            {
                "Tag": 1,
                "Routes": [
                    {
                        "No": "2",
                        "Name": "9th st/hospital",
                        "Destinations": [
                            {
                                "Name": "Downtown",
                                "Trips": [{"ET": None, "ST": "9:30 AM"}],
                            }
                        ],
                    }
                ],
            }
        ],
    }
    await _setup_entry(hass, CONFIG)
    entity_id = er.async_get(hass).async_get_entity_id(
        Platform.SENSOR, TEST_DOMAIN, UNIQUE_ID
    )
    assert entity_id is not None
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "unknown"
    assert state.attributes["scheduled"] == "9:30 AM"


async def test_update_failure_marks_sensor_unavailable(
    hass: HomeAssistant, mock_arrivals: AsyncMock
) -> None:
    """Mark the sensor unavailable after a polling failure."""
    entry = await _setup_entry(hass, CONFIG)
    mock_arrivals.side_effect = CTSApiError("offline")
    await entry.runtime_data.async_refresh()
    entity_id = er.async_get(hass).async_get_entity_id(
        Platform.SENSOR, TEST_DOMAIN, UNIQUE_ID
    )
    assert entity_id is not None
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "unavailable"


async def test_setup_failure_retries(
    hass: HomeAssistant, mock_arrivals: AsyncMock
) -> None:
    """A failed initial request makes setup retry instead of loading entities."""
    mock_arrivals.side_effect = CTSApiError("offline")
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=CONFIG,
        unique_id=UNIQUE_ID,
        title="CTS test",
    )
    entry.add_to_hass(hass)

    assert not await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_RETRY
    assert hass.data.get(DOMAIN, {}) == {}


async def test_shared_coordinator_and_unload(
    hass: HomeAssistant, mock_arrivals: AsyncMock
) -> None:
    """Entries on the same stop share requests and clean up on unload."""
    second_config = {
        **CONFIG,
        "route": "PC",
        "route_name": "philomath/osu",
        "route_label": "PC. philomath/osu",
    }
    first = await _setup_entry(hass, CONFIG)
    second = await _setup_entry(hass, second_config)
    assert first.runtime_data is second.runtime_data
    assert mock_arrivals.await_count == 1
    assert isinstance(first.runtime_data, CTSDataUpdateCoordinator)

    assert await hass.config_entries.async_unload(first.entry_id)
    assert DOMAIN in hass.data
    assert await hass.config_entries.async_unload(second.entry_id)
    assert hass.data[DOMAIN] == {}
