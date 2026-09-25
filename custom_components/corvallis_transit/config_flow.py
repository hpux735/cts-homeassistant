"""Config flow for Corvallis Transit System."""

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


class CTSConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle CTS configuration."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._map_data: dict[str, Any] = {}
        self._projects: dict[str, Mapping[str, Any]] = {}
        self._routes: dict[str, Mapping[str, Any]] = {}
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

        self._projects = {
            str(project["Tag"]): project
            for project in self._map_data.get("Projects", [])
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
            self._data[CONF_ROUTE] = route["No"]
            self._data[CONF_ROUTE_NAME] = route["Name"]
            self._data["route_label"] = (
                f"{route['No']}. {route['Name']}"
                if route.get("No")
                else str(route["Name"])
            )
            return await self.async_step_stop()

        self._routes = {
            _route_key(route): route for route in project.get("Routes", [])
        }
        return self.async_show_form(
            step_id="route",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ROUTE): _selector(
                        {
                            key: (
                                f"{route['No']}. {route['Name']}"
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
        project = self._projects[self._data[CONF_PROJECT]]
        route = next(
            route
            for route in project.get("Routes", [])
            if route.get("No") == self._data[CONF_ROUTE]
            and route.get("Name") == self._data[CONF_ROUTE_NAME]
        )
        platforms = {
            str(platform["Tag"]): platform
            for platform in self._map_data.get("Platforms", [])
            if platform.get("Tag") in route.get("Platforms", [])
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
                {
                    vol.Required(CONF_STOP): _selector(
                        {
                            tag: _platform_label(platform)
                            for tag, platform in platforms.items()
                        }
                    )
                }
            ),
        )
