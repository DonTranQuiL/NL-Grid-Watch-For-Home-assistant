"""Sensors for NL Grid Watch."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, VERSION
from .coordinator import NLGridWatchCoordinator

SENSORS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="afname", translation_key="afname", icon="mdi:transmission-tower"
    ),
    SensorEntityDescription(
        key="teruglevering", translation_key="teruglevering", icon="mdi:solar-power"
    ),
    SensorEntityDescription(
        key="backfeed_risk",
        translation_key="backfeed_risk",
        icon="mdi:white-balance-sunny",
    ),
    SensorEntityDescription(
        key="evening_peak_risk",
        translation_key="evening_peak_risk",
        icon="mdi:weather-night",
    ),
    SensorEntityDescription(
        key="interruption", translation_key="interruption", icon="mdi:flash-off"
    ),
)

DIAGNOSTICS: tuple[tuple[str, str, str, SensorDeviceClass | None], ...] = (
    ("consecutive_errors", "Consecutive errors", "mdi:alert-circle-outline", None),
    ("last_update_status", "Last update status", "mdi:cloud-check-outline", None),
    (
        "last_update_time",
        "Last update time",
        "mdi:clock-outline",
        SensorDeviceClass.TIMESTAMP,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors."""
    coordinator: NLGridWatchCoordinator = entry.runtime_data
    entities: list[SensorEntity] = [
        NLGridWatchSensor(coordinator, entry, description) for description in SENSORS
    ]
    entities.extend(
        NLGridWatchDiagnosticSensor(coordinator, entry, key, name, icon, device_class)
        for key, name, icon, device_class in DIAGNOSTICS
    )
    async_add_entities(entities)


class NLGridWatchSensor(CoordinatorEntity[NLGridWatchCoordinator], RestoreSensor):
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
        self._restored = None
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.title,
            "manufacturer": "DonTranQuiL",
            "model": "NL Grid Watch",
            "sw_version": VERSION,
            "configuration_url": "https://github.com/DonTranQuiL/NL-Grid-Watch-For-Home-assistant",
        }

    async def async_added_to_hass(self) -> None:
        """Restore the last state if the snapshot is not loaded yet."""
        await super().async_added_to_hass()
        last = await self.async_get_last_sensor_data()
        if last is not None:
            self._restored = last.native_value

    @property
    def native_value(self) -> str | None:
        """Return the state."""
        if not self.coordinator.data:
            return self._restored
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
        if not self.coordinator.data:
            return {}
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


class NLGridWatchDiagnosticSensor(
    CoordinatorEntity[NLGridWatchCoordinator], SensorEntity
):
    """Diagnostic health sensors, same block as SkyRadar Fusion."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: NLGridWatchCoordinator,
        entry: ConfigEntry,
        key: str,
        name: str,
        icon: str,
        device_class: SensorDeviceClass | None,
    ) -> None:
        """Initialize the diagnostic sensor."""
        super().__init__(coordinator)
        self._key = key
        self._attr_name = name
        self._attr_icon = icon
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_class = device_class
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.title,
            "manufacturer": "DonTranQuiL",
            "model": "NL Grid Watch",
            "sw_version": VERSION,
        }

    @property
    def native_value(self) -> Any:
        """Return the coordinator health field."""
        return getattr(self.coordinator, self._key, None)


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
