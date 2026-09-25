"""Test the Corvallis Transit System config flow."""

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.const import CONF_STOP
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType, InvalidData
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.corvallis_transit.api import CTSApiError
from custom_components.corvallis_transit.config_flow import (
    CTSConfigFlow,
    _platform_options,
)
from custom_components.corvallis_transit.const import (
    CONF_PROJECT,
    CONF_ROUTE,
    DOMAIN,
)

from .const import CONFIG, MAP_DATA, PROJECT, ROUTE, STOP, UNIQUE_ID


async def test_user_config(hass: HomeAssistant, mock_map_data: AsyncMock) -> None:
    """Configure a route and stop through the UI flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "project"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PROJECT: PROJECT}
    )
    assert result["step_id"] == "route"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_ROUTE: f"{ROUTE}|9th st/hospital"}
    )
    assert result["step_id"] == "stop"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_STOP: STOP}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["route"] == ROUTE
    assert result["data"]["platform_tag"] == STOP
    assert result["result"].unique_id == UNIQUE_ID
    assert mock_map_data.await_count == 1


def test_duplicate_stop_labels_include_direction() -> None:
    """Label duplicate stop names with cardinal directions."""
    options = _platform_options(
        {
            "399": {
                "Tag": 399,
                "No": "#14990",
                "Name": "NW 29th Street & Circle Blvd",
                "X": 10454,
                "Y": 4389,
            },
            "86": {
                "Tag": 86,
                "No": "#12630",
                "Name": "NW 29th St & NW Circle Blvd",
                "X": 10436,
                "Y": 4495,
            },
        }
    )

    assert options["399"] == (
        "NW 29th Street & Circle Blvd (#14990) - Northbound"
    )
    assert options["86"] == "NW 29th St & NW Circle Blvd (#12630) - Southbound"


async def test_connection_failure(hass: HomeAssistant) -> None:
    """Abort when the map endpoint cannot be reached."""
    with patch(
        "custom_components.corvallis_transit.config_flow.async_get_map_data",
        new=AsyncMock(side_effect=CTSApiError),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "cannot_connect"


async def test_no_projects(hass: HomeAssistant) -> None:
    """Abort when the map has no agencies."""
    with patch(
        "custom_components.corvallis_transit.config_flow.async_get_map_data",
        new=AsyncMock(return_value={"Projects": []}),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_projects"


async def test_invalid_project(hass: HomeAssistant, mock_map_data: AsyncMock) -> None:
    """Reject an agency that is not in the selector options."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    with pytest.raises(InvalidData):
        await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_PROJECT: "missing"}
        )


async def test_flow_defensive_validation(hass: HomeAssistant) -> None:
    """Cover defensive checks when a flow is called outside the UI manager."""
    flow = CTSConfigFlow()
    flow.hass = hass
    flow.context = {"source": config_entries.SOURCE_USER}
    flow._projects = {"1": {"Tag": 1, "Name": "CTS", "Routes": []}}
    result = await flow.async_step_project({CONF_PROJECT: "missing"})
    assert result["errors"] == {CONF_PROJECT: "invalid_project"}

    flow._data = {CONF_PROJECT: "1"}
    flow._routes = {}
    result = await flow.async_step_route({CONF_ROUTE: "missing"})
    assert result["errors"] == {CONF_ROUTE: "invalid_route"}

    flow._selected_route = {"No": "1", "Name": "route", "Platforms": [5]}
    flow._map_data = {"Platforms": []}
    result = await flow.async_step_stop({CONF_STOP: "missing"})
    assert result["errors"] == {CONF_STOP: "invalid_stop"}


async def test_invalid_route(hass: HomeAssistant, mock_map_data: AsyncMock) -> None:
    """Reject a route that is not in the selected agency."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PROJECT: PROJECT}
    )
    with pytest.raises(InvalidData):
        await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_ROUTE: "missing"}
        )


async def test_no_routes(hass: HomeAssistant) -> None:
    """Abort when an agency has no routes."""
    map_data = {**MAP_DATA, "Projects": [{"Tag": 1, "Name": "Empty"}]}
    with patch(
        "custom_components.corvallis_transit.config_flow.async_get_map_data",
        new=AsyncMock(return_value=map_data),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_PROJECT: "1"}
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_routes"


async def test_malformed_route_container(hass: HomeAssistant) -> None:
    """Abort instead of crashing when route data is not a list."""
    map_data = {"Projects": [{"Tag": 1, "Name": "Malformed", "Routes": None}]}
    with patch(
        "custom_components.corvallis_transit.config_flow.async_get_map_data",
        new=AsyncMock(return_value=map_data),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_PROJECT: "1"}
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_routes"


async def test_no_stops(hass: HomeAssistant) -> None:
    """Abort when a route has no usable stops."""
    map_data = {
        **MAP_DATA,
        "Projects": [
            {
                "Tag": 1,
                "Name": "Empty stops",
                "Routes": [{"No": "1", "Name": "empty", "Platforms": []}],
            }
        ],
        "Platforms": [],
    }
    with patch(
        "custom_components.corvallis_transit.config_flow.async_get_map_data",
        new=AsyncMock(return_value=map_data),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_PROJECT: "1"}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_ROUTE: "1|empty"}
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_stops"


async def test_malformed_stop_containers(hass: HomeAssistant) -> None:
    """Abort instead of crashing when stop data is malformed."""
    map_data = {
        "Projects": [
            {
                "Tag": 1,
                "Name": "Malformed stops",
                "Routes": [{"No": "1", "Name": "route", "Platforms": None}],
            }
        ],
        "Platforms": None,
    }
    with patch(
        "custom_components.corvallis_transit.config_flow.async_get_map_data",
        new=AsyncMock(return_value=map_data),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_PROJECT: "1"}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_ROUTE: "1|route"}
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_stops"


async def test_invalid_stop(hass: HomeAssistant, mock_map_data: AsyncMock) -> None:
    """Reject a stop that is not served by the selected route."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PROJECT: PROJECT}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_ROUTE: f"{ROUTE}|9th st/hospital"}
    )
    with pytest.raises(InvalidData):
        await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_STOP: "missing"}
        )


async def test_duplicate_entry(hass: HomeAssistant, mock_map_data: AsyncMock) -> None:
    """Do not configure the same route and stop twice."""
    existing = MockConfigEntry(
        domain=DOMAIN,
        title="Existing",
        data=CONFIG,
        unique_id=UNIQUE_ID,
    )
    existing.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PROJECT: PROJECT}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_ROUTE: f"{ROUTE}|9th st/hospital"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_STOP: STOP}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
