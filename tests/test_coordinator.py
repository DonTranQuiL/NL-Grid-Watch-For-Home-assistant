"""Unit tests for the risk scorer (no network)."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import patch

from homeassistant.util import dt as dt_util

from custom_components.nl_grid_watch.coordinator import score_risk


def _hours(base: datetime, specs: list[tuple[int, float, float, float]]):
    rows = []
    for hour, radiation, cloud, temp in specs:
        stamp = (
            base.replace(minute=0, second=0, microsecond=0)
            + timedelta(hours=hour - base.hour)
        ).isoformat()
        rows.append(
            {
                "time": stamp,
                "radiation": radiation,
                "cloud": cloud,
                "temperature": temp,
            }
        )
    return rows


def test_backfeed_high_when_queue_and_sunny():
    now = datetime(2026, 6, 15, 9, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE)
    forecast = _hours(
        now,
        [
            (11, 600, 20, 22),
            (12, 700, 10, 23),
            (13, 650, 15, 24),
        ],
    )
    capacity = {
        "afname": {"status": "available"},
        "teruglevering": {"status": "queue"},
    }
    with patch(
        "custom_components.nl_grid_watch.coordinator.dt_util.now", return_value=now
    ):
        risk = score_risk(capacity, forecast)
    assert risk["backfeed_risk"] == "high"
    assert risk["stress_expected"] is True
    assert risk["active_window"] == "backfeed"


def test_evening_high_when_investigation_and_dark_cold():
    now = datetime(2026, 1, 10, 14, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE)
    forecast = _hours(
        now,
        [
            (17, 50, 80, 2),
            (18, 20, 90, 1),
            (19, 10, 85, 0),
        ],
    )
    capacity = {
        "afname": {"status": "investigation"},
        "teruglevering": {"status": "available"},
    }
    with patch(
        "custom_components.nl_grid_watch.coordinator.dt_util.now", return_value=now
    ):
        risk = score_risk(capacity, forecast)
    assert risk["evening_peak_risk"] == "high"
    assert risk["stress_expected"] is True
    assert risk["active_window"] == "evening_peak"


def test_none_when_capacity_available():
    now = datetime(2026, 6, 15, 9, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE)
    forecast = _hours(now, [(12, 700, 10, 22)])
    capacity = {
        "afname": {"status": "available"},
        "teruglevering": {"status": "available"},
    }
    with patch(
        "custom_components.nl_grid_watch.coordinator.dt_util.now", return_value=now
    ):
        risk = score_risk(capacity, forecast)
    assert risk["backfeed_risk"] == "none"
    assert risk["evening_peak_risk"] == "none"
    assert risk["stress_expected"] is False
