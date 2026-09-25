"""Corvallis Transit System integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_STOP, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.hass_dict import HassKey

from .const import CONF_PLATFORM_TAG, DOMAIN
from .coordinator import CTSDataUpdateCoordinator

PLATFORMS = [Platform.SENSOR]

type CTSConfigEntry = ConfigEntry[CTSDataUpdateCoordinator]

CTS_COORDINATORS: HassKey[dict[str, CTSDataUpdateCoordinator]] = HassKey(DOMAIN)


async def async_setup_entry(hass: HomeAssistant, entry: CTSConfigEntry) -> bool:
    """Set up a Corvallis Transit System config entry."""
    platform_tag = str(entry.data[CONF_PLATFORM_TAG])
    coordinators = hass.data.setdefault(CTS_COORDINATORS, {})
    coordinator = coordinators.get(platform_tag)
    if coordinator is None:
        coordinator = CTSDataUpdateCoordinator(hass, int(entry.data[CONF_STOP]))
        coordinators[platform_tag] = coordinator

    coordinator.add_entry(entry.entry_id)
    entry.runtime_data = coordinator

    await coordinator.async_refresh()
    if not coordinator.last_update_success:
        coordinator.remove_entry(entry.entry_id)
        if not coordinator.has_entries():
            await coordinator.async_shutdown()
            coordinators.pop(platform_tag, None)
        raise ConfigEntryNotReady from coordinator.last_exception

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: CTSConfigEntry) -> bool:
    """Unload a Corvallis Transit System config entry."""
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False

    coordinator = entry.runtime_data
    coordinator.remove_entry(entry.entry_id)
    if not coordinator.has_entries():
        await coordinator.async_shutdown()
        hass.data[CTS_COORDINATORS].pop(str(entry.data[CONF_PLATFORM_TAG]), None)

    return True
