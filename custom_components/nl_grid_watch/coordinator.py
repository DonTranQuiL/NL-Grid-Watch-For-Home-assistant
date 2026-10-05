"""Data coordinator for NL Grid Watch."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import NLGridWatchApi
from .const import (
    BACKFEED_HOURS,
    CLOUD_CLEAR,
    CLOUD_DARK,
    COLD_EVENING,
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_POSTAL_CODE,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    EVENING_HOURS,
    NAME,
    SOLAR_HIGH,
    SOLAR_LOW,
)

TIGHT = {"investigation", "queue"}
WATCH = {"limited", "investigation", "queue"}


def _parse_local(stamp: str) -> datetime:
    """Parse an Open-Meteo local timestamp."""
    parsed = datetime.fromisoformat(stamp)
    if parsed.tzinfo is None:
        return dt_util.as_local(parsed)
    return parsed


def _window(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Describe the first and last hour of a matching run."""
    if not rows:
        return None
    return {
        "start": rows[0]["time"],
        "end": rows[-1]["time"],
        "peak_radiation": max((row.get("radiation") or 0) for row in rows),
        "min_temperature": min((row.get("temperature") or 99) for row in rows),
        "hours": len(rows),
    }


def score_risk(capacity: dict[str, Any], forecast: list[dict[str, Any]]) -> dict[str, Any]:
    """Score backfeed and evening-peak risk from area colour and weather."""
    now = dt_util.now()
    future = [row for row in forecast if _parse_local(row["time"]) >= now - timedelta(minutes=30)]
    afname = (capacity.get("afname") or {}).get("status", "unknown")
    terug = (capacity.get("teruglevering") or {}).get("status", "unknown")

    sunny = [
        row
        for row in future
        if _parse_local(row["time"]).hour in BACKFEED_HOURS
        and (row.get("radiation") or 0) >= SOLAR_HIGH
        and (row.get("cloud") or 100) <= CLOUD_CLEAR
    ]
    bright = [
        row
        for row in future
        if _parse_local(row["time"]).hour in BACKFEED_HOURS
        and (row.get("radiation") or 0) >= SOLAR_LOW
    ]
    dark_cold = [
        row
        for row in future
        if _parse_local(row["time"]).hour in EVENING_HOURS
        and (
            (row.get("cloud") or 0) >= CLOUD_DARK
            or (row.get("temperature") or 99) <= COLD_EVENING
            or _parse_local(row["time"]).month in {11, 12, 1, 2}
        )
    ]

    if terug in TIGHT and sunny:
        backfeed = "high"
    elif terug in WATCH and bright:
        backfeed = "low"
    else:
        backfeed = "none"

    if afname in TIGHT and dark_cold:
        evening = "high"
    elif afname in WATCH and dark_cold:
        evening = "low"
    else:
        evening = "none"

    active = "backfeed" if backfeed == "high" else "evening_peak" if evening == "high" else "none"
    return {
        "backfeed_risk": backfeed,
        "evening_peak_risk": evening,
        "stress_expected": backfeed == "high" or evening == "high",
        "active_window": active,
        "backfeed_window": _window(sunny or bright),
        "evening_window": _window(dark_cold),
    }


class NLGridWatchCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Poll capacity, weather and optional interruptions."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        super().__init__(
            hass,
            name=DOMAIN,
            update_interval=timedelta(minutes=interval),
            config_entry=entry,
        )
        self.entry = entry
        self.api = NLGridWatchApi(hass)
        self.postal_code = entry.data[CONF_POSTAL_CODE]

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch all sources and score the next windows."""
        try:
            place = await self.api.async_geocode(self.postal_code)
            capacity = await self.api.async_capacity(place["latitude"], place["longitude"])
            forecast = await self.api.async_forecast(place["latitude"], place["longitude"])
            disruptions: dict[str, Any] = {"enabled": False, "items": [], "error": None}
            client_id = self.entry.data.get(CONF_CLIENT_ID, "")
            client_secret = self.entry.data.get(CONF_CLIENT_SECRET, "")
            if client_id and client_secret:
                try:
                    disruptions = await self.api.async_disruptions(
                        self.postal_code, client_id, client_secret
                    )
                    disruptions["error"] = None
                except Exception as err:  # noqa: BLE001 - keep the forecast if the extra feed fails
                    disruptions = {"enabled": True, "items": [], "error": str(err)}
        except Exception as err:
            raise UpdateFailed(str(err)) from err

        risk = score_risk(capacity, forecast)
        return {
            "place": place,
            "capacity": capacity,
            "forecast": forecast[:48],
            "disruptions": disruptions,
            "risk": risk,
            "name": NAME,
        }
