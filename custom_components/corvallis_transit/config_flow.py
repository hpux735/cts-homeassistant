"""Config flow for Corvallis Transit System."""

import re
from collections.abc import Mapping
from typing import Any, override

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_STOP
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .api import CTSApiError, async_get_map_data
from .const import (
    CONF_PLATFORM_NAME,
    CONF_PLATFORM_TAG,
    CONF_PROJECT,
    CONF_ROUTE,
    CONF_ROUTE_NAME,
    DOMAIN,
)


def _selector(options: Mapping[str, str]) -> SelectSelector:
    """Create a sorted dropdown selector."""
    return SelectSelector(
        SelectSelectorConfig(
            options=sorted(
                (
                    SelectOptionDict(value=value, label=label)
                    for value, label in options.items()
                ),
                key=lambda option: option["label"],
            ),
            mode=SelectSelectorMode.DROPDOWN,
        )
    )


def _route_key(route: Mapping[str, Any]) -> str:
    """Build a stable route selection key."""
    return f"{route.get('No', '')}|{route['Name']}"


def _platform_label(platform: Mapping[str, Any]) -> str:
    """Return a useful stop label."""
    number = platform.get("No") or platform.get("Nos")
    return f"{platform['Name']} ({number})" if number else str(platform["Name"])


def _platform_options(
    platforms: Mapping[str, Mapping[str, Any]],
) -> dict[str, str]:
    """Build stop labels, adding cardinal direction for duplicate stop names."""
    by_name: dict[str, list[Mapping[str, Any]]] = {}
    for platform in platforms.values():
        by_name.setdefault(_stop_match_key(str(platform["Name"])), []).append(platform)

    options: dict[str, str] = {}
    for tag, platform in platforms.items():
        peers = by_name[_stop_match_key(str(platform["Name"]))]
        direction = None
        if len(peers) > 1:
            coordinates = [
                (peer.get("X"), peer.get("Y"))
                for peer in peers
                if isinstance(peer.get("X"), (int, float))
                and isinstance(peer.get("Y"), (int, float))
            ]
            if len(coordinates) == len(peers):
                x_range = max(x for x, _ in coordinates) - min(
                    x for x, _ in coordinates
                )
                y_range = max(y for _, y in coordinates) - min(
                    y for _, y in coordinates
                )
                if x_range <= 250 and y_range <= 250:
                    if y_range >= x_range:
                        direction = (
                            "Northbound"
                            if platform["Y"] == min(y for _, y in coordinates)
                            else "Southbound"
                        )
                    else:
                        direction = (
                            "Westbound"
                            if platform["X"] == min(x for x, _ in coordinates)
                            else "Eastbound"
                        )

        label = _platform_label(platform)
        options[tag] = f"{label} - {direction}" if direction else label
    return options


def _stop_match_key(name: str) -> str:
    """Normalize intersection names for matching opposite-side stops."""
    normalized = name.casefold()
    for word, replacement in {
        "northwest": "nw",
        "northeast": "ne",
        "southwest": "sw",
        "southeast": "se",
        "street": "st",
        "avenue": "ave",
        "boulevard": "blvd",
        "road": "rd",
        "drive": "dr",
        "highway": "hwy",
    }.items():
        normalized = re.sub(rf"\b{word}\b", replacement, normalized)
    normalized = re.sub(r"\b(?:n|s|e|w|ne|nw|se|sw)\b", "", normalized)
    return re.sub(r"[^a-z0-9]+", "", normalized)


class CTSConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle CTS configuration."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._map_data: dict[str, Any] = {}
        self._projects: dict[str, Mapping[str, Any]] = {}
        self._routes: dict[str, Mapping[str, Any]] = {}
        self._selected_route: Mapping[str, Any] | None = None
        self._data: dict[str, Any] = {}

    @override
    async def async_step_user(
        self, user_input: dict[str, str] | None = None
    ) -> ConfigFlowResult:
        """Start configuration."""
        try:
            self._map_data = await async_get_map_data(self.hass)
        except CTSApiError:
            return self.async_abort(reason="cannot_connect")

        projects = self._map_data.get("Projects", [])
        if not isinstance(projects, list):
            projects = []
        self._projects = {
            str(project["Tag"]): project
            for project in projects
            if isinstance(project, Mapping)
            and "Tag" in project
            and isinstance(project.get("Name"), str)
        }
        if not self._projects:
            return self.async_abort(reason="no_projects")
        return await self.async_step_project(user_input)

    async def async_step_project(
        self, user_input: dict[str, str] | None = None
    ) -> ConfigFlowResult:
        """Select the transit agency."""
        if user_input is not None:
            project = self._projects.get(user_input[CONF_PROJECT])
            if project is None:
                return self.async_show_form(
                    step_id="project", errors={CONF_PROJECT: "invalid_project"}
                )
            self._data[CONF_PROJECT] = user_input[CONF_PROJECT]
            self._data["project_name"] = project["Name"]
            return await self.async_step_route()

        return self.async_show_form(
            step_id="project",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PROJECT): _selector(
                        {
                            tag: str(project["Name"])
                            for tag, project in self._projects.items()
                        }
                    )
                }
            ),
        )

    async def async_step_route(
        self, user_input: dict[str, str] | None = None
    ) -> ConfigFlowResult:
        """Select a route."""
        project = self._projects[self._data[CONF_PROJECT]]
        if user_input is not None:
            route = self._routes.get(user_input[CONF_ROUTE])
            if route is None:
                return self.async_show_form(
                    step_id="route", errors={CONF_ROUTE: "invalid_route"}
                )
            self._data[CONF_ROUTE] = str(route.get("No", ""))
            self._data[CONF_ROUTE_NAME] = route["Name"]
            self._selected_route = route
            self._data["route_label"] = (
                f"{route.get('No')}. {route['Name']}"
                if route.get("No")
                else str(route["Name"])
            )
            return await self.async_step_stop()

        route_list = project.get("Routes", [])
        if not isinstance(route_list, list):
            route_list = []
        self._routes = {
            _route_key(route): route
            for route in route_list
            if isinstance(route, Mapping) and isinstance(route.get("Name"), str)
        }
        if not self._routes:
            return self.async_abort(reason="no_routes")
        return self.async_show_form(
            step_id="route",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ROUTE): _selector(
                        {
                            key: (
                                f"{route.get('No')}. {route['Name']}"
                                if route.get("No")
                                else str(route["Name"])
                            )
                            for key, route in self._routes.items()
                        }
                    )
                }
            ),
        )

    async def async_step_stop(
        self, user_input: dict[str, str] | None = None
    ) -> ConfigFlowResult:
        """Select a stop."""
        route = self._selected_route
        if route is None:
            return self.async_abort(reason="no_routes")
        platform_list = self._map_data.get("Platforms", [])
        if not isinstance(platform_list, list):
            platform_list = []
        route_platforms = route.get("Platforms", [])
        if not isinstance(route_platforms, list):
            route_platforms = []
        platforms = {
            str(platform["Tag"]): platform
            for platform in platform_list
            if isinstance(platform, Mapping)
            and "Tag" in platform
            and isinstance(platform.get("Name"), str)
            and platform.get("Tag") in route_platforms
        }
        if user_input is not None:
            platform = platforms.get(user_input[CONF_STOP])
            if platform is None:
                return self.async_show_form(
                    step_id="stop", errors={CONF_STOP: "invalid_stop"}
                )

            self._data[CONF_STOP] = user_input[CONF_STOP]
            self._data[CONF_PLATFORM_TAG] = user_input[CONF_STOP]
            self._data[CONF_PLATFORM_NAME] = platform["Name"]
            unique_id = (
                f"{self._data[CONF_PROJECT]}_{self._data[CONF_ROUTE]}_"
                f"{self._data[CONF_PLATFORM_TAG]}"
            )
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=(
                    f"{self._data['project_name']} - {self._data['route_label']} - "
                    f"{self._data[CONF_PLATFORM_NAME]}"
                ),
                data=self._data,
            )

        if not platforms:
            return self.async_abort(reason="no_stops")
        return self.async_show_form(
            step_id="stop",
            data_schema=vol.Schema(
                {vol.Required(CONF_STOP): _selector(_platform_options(platforms))}
            ),
        )
