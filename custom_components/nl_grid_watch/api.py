"""HTTP clients for postcode, capacity, weather and interruptions."""

from __future__ import annotations

import re
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CAPACITY_LAYERS,
    EO_DISRUPTIONS_URL,
    EO_TOKEN_URL,
    OPEN_METEO_URL,
    PDOK_URL,
    STATUS_LABELS,
)

POINT_RE = re.compile(r"POINT\(([0-9.]+)\s+([0-9.]+)\)")


class NLGridWatchApi:
    """Fetch the public sources used by the forecast."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the API."""
        self._session = async_get_clientsession(hass)

    async def async_geocode(self, postal_code: str) -> dict[str, Any]:
        """Resolve a Dutch postcode to a WGS84 point."""
        async with self._session.get(
            PDOK_URL,
            params={"q": postal_code, "fq": "type:postcode", "rows": 1},
            timeout=20,
        ) as response:
            response.raise_for_status()
            payload = await response.json()
        docs = payload.get("response", {}).get("docs") or []
        if not docs:
            raise LookupError(f"Postcode {postal_code} was not found")
        match = POINT_RE.search(docs[0].get("centroide_ll", ""))
        if not match:
            raise LookupError("PDOK did not return a coordinate")
        return {
            "postal_code": postal_code,
            "name": docs[0].get("weergavenaam"),
            "longitude": float(match.group(1)),
            "latitude": float(match.group(2)),
        }

    async def async_capacity(self, latitude: float, longitude: float) -> dict[str, Any]:
        """Return afname and teruglevering status for a point."""
        result: dict[str, Any] = {}
        for key, url in CAPACITY_LAYERS.items():
            async with self._session.get(
                url,
                params={
                    "f": "json",
                    "geometry": f"{longitude},{latitude}",
                    "geometryType": "esriGeometryPoint",
                    "inSR": "4326",
                    "spatialRel": "esriSpatialRelIntersects",
                    "outFields": "*",
                    "returnGeometry": "false",
                },
                timeout=30,
            ) as response:
                response.raise_for_status()
                payload = await response.json()
            features = payload.get("features") or []
            if not features:
                result[key] = {"status": "unknown", "code": None}
                continue
            attrs = features[0]["attributes"]
            code = attrs.get("afname" if key == "afname" else "opwek")
            result[key] = {
                "status": STATUS_LABELS.get(code, "unknown"),
                "code": code,
                "area": attrs.get("voedingsgebied_naam"),
                "area_id": attrs.get("voedingsgebied_id"),
                "operator": attrs.get("RNB"),
                "queue_mw": attrs.get(
                    "wachtrij_afname" if key == "afname" else "wachtrij_invoeding"
                ),
                "requests": attrs.get(
                    "unieke_verzoeken_afname"
                    if key == "afname"
                    else "unieke_verzoeken_invoeding"
                ),
            }
        return result

    async def async_forecast(self, latitude: float, longitude: float) -> list[dict[str, Any]]:
        """Return hourly weather for the next two days."""
        async with self._session.get(
            OPEN_METEO_URL,
            params={
                "latitude": latitude,
                "longitude": longitude,
                "hourly": "temperature_2m,cloud_cover,shortwave_radiation",
                "timezone": "Europe/Amsterdam",
                "forecast_days": 2,
            },
            timeout=20,
        ) as response:
            response.raise_for_status()
            payload = await response.json()
        hourly = payload.get("hourly") or {}
        times = hourly.get("time") or []
        rows = []
        for index, stamp in enumerate(times):
            rows.append(
                {
                    "time": stamp,
                    "temperature": (hourly.get("temperature_2m") or [None])[index],
                    "cloud": (hourly.get("cloud_cover") or [None])[index],
                    "radiation": (hourly.get("shortwave_radiation") or [None])[index],
                }
            )
        return rows

    async def async_disruptions(
        self, postal_code: str, client_id: str, client_secret: str
    ) -> dict[str, Any]:
        """Return electricity interruptions when credentials are configured."""
        if not client_id or not client_secret:
            return {"enabled": False, "items": []}
        async with self._session.post(
            EO_TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
            },
            timeout=20,
        ) as response:
            if response.status >= 400:
                body = await response.text()
                raise PermissionError(
                    f"energieonderbrekingen token failed: {response.status} {body[:180]}"
                )
            token_payload = await response.json()
        token = token_payload.get("access_token")
        if not token:
            raise PermissionError("energieonderbrekingen did not return a token")
        async with self._session.get(
            EO_DISRUPTIONS_URL,
            params={
                "postalCode": postal_code,
                "network[]": "electricity",
                "limit": 20,
            },
            headers={"Authorization": f"Bearer {token}"},
            timeout=20,
        ) as response:
            response.raise_for_status()
            payload = await response.json()
        items = payload if isinstance(payload, list) else payload.get("data") or payload.get("items") or []
        return {"enabled": True, "items": items}
