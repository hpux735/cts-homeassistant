"""Sensors for Corvallis Transit System."""

from datetime import timedelta
from typing import Any, cast, override

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import CONF_NAME, CONF_STOP
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from . import CTSConfigEntry
from .const import (
    CONF_PLATFORM_NAME,
    CONF_PROJECT,
    CONF_ROUTE,
    CONF_ROUTE_NAME,
    DOMAIN,
)
from .coordinator import CTSDataUpdateCoordinator

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CTSConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up a CTS arrival sensor."""
    async_add_entities(
        [
            CTSNextBusSensor(
                entry.runtime_data,
                cast(str, entry.unique_id),
                int(entry.data[CONF_PROJECT]),
                str(entry.data[CONF_ROUTE]),
                str(entry.data[CONF_ROUTE_NAME]),
                str(entry.data[CONF_STOP]),
                str(entry.data[CONF_PLATFORM_NAME]),
                entry.data.get(CONF_NAME) or entry.title,
            )
        ]
    )


class CTSNextBusSensor(CoordinatorEntity[CTSDataUpdateCoordinator], SensorEntity):
    """Display the next live CTS arrival for one route and stop."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_has_entity_name = True
    _attr_translation_key = "next_bus"

    def __init__(
        self,
        coordinator: CTSDataUpdateCoordinator,
        unique_id: str,
        project_tag: int,
        route_no: str,
        route_name: str,
        stop_tag: str,
        stop_name: str,
        name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.project_tag = project_tag
        self.route_no = route_no
        self.route_name = route_name
        self.stop_tag = stop_tag
        self.stop_name = stop_name
        self._attr_unique_id = unique_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, unique_id)},
            name=name,
            manufacturer="Corvallis Transit System",
            model=f"Route {route_no}",
            configuration_url="https://www.corvallistransit.com/rtt/public/",
        )
        self._attr_extra_state_attributes = {
            "project": project_tag,
            "route": route_no,
            "route_name": route_name,
            "stop": stop_tag,
            "stop_name": stop_name,
        }

    async def async_added_to_hass(self) -> None:
        """Render the initial coordinator data when the entity is added."""
        self._handle_coordinator_update()
        await super().async_added_to_hass()

    @callback
    @override
    def _handle_coordinator_update(self) -> None:
        """Update the sensor from the shared platform response."""
        data = self.coordinator.data
        if not isinstance(data, dict):
            data = {}
        trips: list[dict[str, Any]] = []
        destinations: set[str] = set()

        projects = data.get("Projects", [])
        if not isinstance(projects, list):
            projects = []

        for project in projects:
            if not isinstance(project, dict):
                continue
            if project.get("Tag") != self.project_tag:
                continue
            routes = project.get("Routes", [])
            if not isinstance(routes, list):
                continue
            for route in routes:
                if not isinstance(route, dict):
                    continue
                if (
                    route.get("No") != self.route_no
                    or route.get("Name") != self.route_name
                ):
                    continue
                destinations_for_route = route.get("Destinations", [])
                if not isinstance(destinations_for_route, list):
                    continue
                for destination in destinations_for_route:
                    if not isinstance(destination, dict):
                        continue
                    destinations.add(str(destination.get("Name", "")))
                    destination_trips = destination.get("Trips", [])
                    if isinstance(destination_trips, list):
                        trips.extend(
                            trip for trip in destination_trips if isinstance(trip, dict)
                        )

        live_trips: list[tuple[int, dict[str, Any]]] = []
        for trip in trips:
            eta = trip.get("ET")
            if eta is None or isinstance(eta, bool):
                continue
            try:
                live_trips.append((int(eta), trip))
            except (TypeError, ValueError):
                continue
        live_trips.sort(key=lambda trip: trip[0])
        scheduled_trips = [trip for trip in trips if trip.get("ST") is not None]

        self._attr_extra_state_attributes["destination"] = ", ".join(
            sorted(destination for destination in destinations if destination)
        )
        self._attr_extra_state_attributes["updated_at"] = data.get("Created")

        if live_trips:
            self._attr_native_value = dt_util.utcnow() + timedelta(
                minutes=live_trips[0][0]
            )
            self._attr_extra_state_attributes["upcoming"] = ", ".join(
                str(trip[0]) for trip in live_trips
            )
            self._attr_extra_state_attributes.pop("scheduled", None)
        elif scheduled_trips:
            self._attr_native_value = None
            self._attr_extra_state_attributes.pop("upcoming", None)
            self._attr_extra_state_attributes["scheduled"] = ", ".join(
                str(trip["ST"]) for trip in scheduled_trips
            )
        else:
            self._attr_native_value = None
            self._attr_extra_state_attributes.pop("upcoming", None)
            self._attr_extra_state_attributes.pop("scheduled", None)

        self.async_write_ha_state()
