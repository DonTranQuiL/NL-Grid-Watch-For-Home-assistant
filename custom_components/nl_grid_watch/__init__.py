"""The NL Grid Watch integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall

from .const import DOMAIN, PLATFORMS
from .coordinator import NLGridWatchCoordinator

type NLGridWatchConfigEntry = ConfigEntry[NLGridWatchCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: NLGridWatchConfigEntry) -> bool:
    """Set up NL Grid Watch from a config entry."""
    coordinator = NLGridWatchCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    async def handle_refresh(call: ServiceCall) -> None:
        """Force a refresh of every configured entry."""
        for item in hass.config_entries.async_entries(DOMAIN):
            runtime = getattr(item, "runtime_data", None)
            if runtime is not None:
                await runtime.async_request_refresh()

    hass.services.async_register(DOMAIN, "refresh", handle_refresh)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    await hass.config_entries.async_forward_entry_setups(entry, [Platform(p) for p in PLATFORMS])
    return True


async def async_unload_entry(hass: HomeAssistant, entry: NLGridWatchConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded and not hass.config_entries.async_entries(DOMAIN):
        hass.services.async_remove(DOMAIN, "refresh")
    return unloaded


async def async_reload_entry(hass: HomeAssistant, entry: NLGridWatchConfigEntry) -> None:
    """Reload when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
