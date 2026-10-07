"""Smoke tests for package constants and manifest."""

from __future__ import annotations

import json
from pathlib import Path

from custom_components.nl_grid_watch.const import DOMAIN, PLATFORMS, VERSION


def test_domain_and_version():
    assert DOMAIN == "nl_grid_watch"
    manifest = json.loads(
        (
            Path(__file__).resolve().parents[1]
            / "custom_components"
            / "nl_grid_watch"
            / "manifest.json"
        ).read_text()
    )
    assert VERSION == manifest["version"]
    assert set(PLATFORMS) == {"sensor", "binary_sensor"}


def test_manifest_urls():
    manifest = json.loads(
        (
            Path(__file__).resolve().parents[1]
            / "custom_components"
            / "nl_grid_watch"
            / "manifest.json"
        ).read_text(encoding="utf-8")
    )
    assert (
        manifest["documentation"]
        == "https://github.com/DonTranQuiL/NL-Grid-Watch-For-Home-assistant"
    )
    assert (
        manifest["issue_tracker"]
        == "https://github.com/DonTranQuiL/NL-Grid-Watch-For-Home-assistant/issues"
    )
    assert manifest["config_flow"] is True
    assert manifest["version"] == VERSION
    assert manifest["domain"] == DOMAIN
