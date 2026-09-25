"""Data update coordinator for Corvallis Transit System."""

import logging
from datetime import timedelta
from typing import Any, override

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import CTSApiError, async_get_platform_arrivals
from .const import DOMAIN, UPDATE_INTERVAL_MINUTES

_LOGGER = logging.getLogger(__name__)


class CTSDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetch one shared arrival response for a CTS platform."""

    def __init__(self, hass: HomeAssistant, platform_tag: int) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=None,
            name=DOMAIN,
            update_interval=timedelta(minutes=UPDATE_INTERVAL_MINUTES),
        )
        self.platform_tag = platform_tag
        self._entries: set[str] = set()

    def add_entry(self, entry_id: str) -> None:
        """Register an entry using this platform response."""
        self._entries.add(entry_id)

    def remove_entry(self, entry_id: str) -> None:
        """Unregister an entry using this platform response."""
        self._entries.discard(entry_id)

    def has_entries(self) -> bool:
        """Return whether any config entries still use this coordinator."""
        return bool(self._entries)

    @override
    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch arrival data from CTS."""
        try:
            return await async_get_platform_arrivals(self.hass, self.platform_tag)
        except CTSApiError as err:
            raise UpdateFailed("Failed to fetch Corvallis Transit arrivals") from err
