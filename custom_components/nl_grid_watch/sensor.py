"""Sensors for NL Grid Watch."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import NLGridWatchCoordinator

SENSORS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(key="afname", translation_key="afname", icon="mdi:transmission-tower"),
    SensorEntityDescription(
        key="teruglevering", translation_key="teruglevering", icon="mdi:solar-power"
    ),
    SensorEntityDescription(
        key="backfeed_risk", translation_key="backfeed_risk", icon="mdi:white-balance-sunny"
    ),
    SensorEntityDescription(
        key="evening_peak_risk", translation_key="evening_peak_risk", icon="mdi:weather-night"
    ),
    SensorEntityDescription(key="interruption", translation_key="interruption", icon="mdi:flash-off"),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors."""
    coordinator: NLGridWatchCoordinator = entry.runtime_data
    async_add_entities(NLGridWatchSensor(coordinator, entry, description) for description in SENSORS)


class NLGridWatchSensor(CoordinatorEntity[NLGridWatchCoordinator], SensorEntity):
    """A forecast or area sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: NLGridWatchCoordinator,
        entry: ConfigEntry,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = {
            "identifiers": {("nl_grid_watch", entry.entry_id)},
            "name": entry.title,
            "manufacturer": "DonTranQuiL",
            "model": "NL Grid Watch",
            "configuration_url": "https://github.com/DonTranQuiL/NL-Grid-Watch-For-Home-assistant",
        }

    @property
    def native_value(self) -> str | None:
        """Return the state."""
        data = self.coordinator.data
        key = self.entity_description.key
        if key in {"afname", "teruglevering"}:
            return (data["capacity"].get(key) or {}).get("status", "unknown")
        if key == "backfeed_risk":
            return data["risk"]["backfeed_risk"]
        if key == "evening_peak_risk":
            return data["risk"]["evening_peak_risk"]
        return _interruption_state(data["disruptions"])

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the details used by automations."""
        data = self.coordinator.data
        key = self.entity_description.key
        place = data["place"]
        if key in {"afname", "teruglevering"}:
            area = data["capacity"].get(key) or {}
            return {**area, "postal_code": place["postal_code"], "place": place["name"]}
        if key == "backfeed_risk":
            return {"window": data["risk"]["backfeed_window"], "place": place["name"]}
        if key == "evening_peak_risk":
            return {"window": data["risk"]["evening_window"], "place": place["name"]}
        items = data["disruptions"].get("items") or []
        return {
            "enabled": data["disruptions"].get("enabled"),
            "error": data["disruptions"].get("error"),
            "count": len(items),
            "items": items[:5],
        }


def _interruption_state(disruptions: dict[str, Any]) -> str:
    """Summarise the optional interruption feed."""
    if disruptions.get("error"):
        return "error"
    if not disruptions.get("enabled"):
        return "not_configured"
    items = disruptions.get("items") or []
    if not items:
        return "none"
    first = items[0] if isinstance(items[0], dict) else {}
    if first.get("planned") or first.get("maintenance"):
        return "planned"
    return "active"
