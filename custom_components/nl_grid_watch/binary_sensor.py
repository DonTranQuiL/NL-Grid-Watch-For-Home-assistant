"""Binary sensor for an expected stress window."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import NLGridWatchCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the stress binary sensor."""
    async_add_entities([NLGridWatchStressSensor(entry.runtime_data, entry)])


class NLGridWatchStressSensor(CoordinatorEntity[NLGridWatchCoordinator], BinarySensorEntity):
    """On when either forecast window is high."""

    _attr_has_entity_name = True
    _attr_translation_key = "stress_expected"
    _attr_device_class = BinarySensorDeviceClass.SAFETY

    def __init__(self, coordinator: NLGridWatchCoordinator, entry: ConfigEntry) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_stress_expected"
        self._attr_device_info = {
            "identifiers": {("nl_grid_watch", entry.entry_id)},
            "name": entry.title,
            "manufacturer": "DonTranQuiL",
            "model": "NL Grid Watch",
        }

    @property
    def is_on(self) -> bool:
        """Return true when a high-risk window is ahead."""
        return bool(self.coordinator.data["risk"]["stress_expected"])

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return which window triggered."""
        risk = self.coordinator.data["risk"]
        return {
            "active_window": risk["active_window"],
            "backfeed_risk": risk["backfeed_risk"],
            "evening_peak_risk": risk["evening_peak_risk"],
            "backfeed_window": risk["backfeed_window"],
            "evening_window": risk["evening_window"],
        }
