"""Sensors for Corvallis Transit System."""

from datetime import timedelta
import logging
from typing import Any, cast, override

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import CONF_NAME, CONF_STOP
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from . import CTSConfigEntry
from .const import (
    CONF_PLATFORM_NAME,
    CONF_PROJECT,
    CONF_ROUTE,
    CONF_ROUTE_NAME,
)
from .coordinator import CTSDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


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
        self._attr_name = name
        self._attr_extra_state_attributes = {
            "project": project_tag,
            "route": route_no,
            "route_name": route_name,
            "stop": stop_tag,
            "stop_name": stop_name,
        }

    @callback
    @override
    def _handle_coordinator_update(self) -> None:
        """Update the sensor from the shared platform response."""
        data = self.coordinator.data or {}
        trips: list[dict[str, Any]] = []
        destinations: set[str] = set()

        for project in data.get("Projects", []):
            if project.get("Tag") != self.project_tag:
                continue
            for route in project.get("Routes", []):
                if (
                    route.get("No") != self.route_no
                    or route.get("Name") != self.route_name
                ):
                    continue
                for destination in route.get("Destinations", []):
                    destinations.add(str(destination.get("Name", "")))
                    trips.extend(destination.get("Trips", []))

        live_trips = [trip for trip in trips if trip.get("ET") is not None]
        live_trips.sort(key=lambda trip: trip["ET"])
        scheduled_trips = [trip for trip in trips if trip.get("ST") is not None]

        self._attr_extra_state_attributes["destination"] = ", ".join(
            sorted(destination for destination in destinations if destination)
        )
        self._attr_extra_state_attributes["updated_at"] = data.get("Created")

        if live_trips:
            self._attr_native_value = dt_util.utcnow() + timedelta(
                minutes=int(live_trips[0]["ET"])
            )
            self._attr_extra_state_attributes["upcoming"] = ", ".join(
                str(trip["ET"]) for trip in live_trips
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
