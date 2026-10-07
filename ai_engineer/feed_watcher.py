#!/usr/bin/env python3
"""Watch the upstream sources NL Grid Watch depends on for breaking changes.

Sources (see custom_components/nl_grid_watch/api.py):
  * PDOK Locatieserver: postcode -> WGS84 point (``centroide_ll``)
  * Netbeheer Nederland capacity map (ArcGIS FeatureServer), afname and
    teruglevering layers: status codes, area, operator, queue fields
  * Open-Meteo: hourly temperature, cloud cover and shortwave radiation
  * energieonderbrekingen.nl: OAuth token + disruptions endpoints (reachability only;
    they need user credentials)

Detection is deterministic: each source is reduced to a stable fingerprint
(reachability, field names and the fields the integration needs). The
fingerprint is stored in .memory/nl_grid_sources.json. An issue is opened only
when a source *newly* loses a required field or disappears (404/410), so a
persistent breakage is reported once. Timeouts and 5xx are treated as transient.
An optional LLM (xAI first, then OpenRouter) adds a short impact summary.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import requests

COMPONENT = "custom_components/nl_grid_watch/"
MEMORY_PATH = Path(".memory/nl_grid_sources.json")
REPORT_PATH = Path("feed_watch_report.md")
HEADERS = {"User-Agent": "HomeAssistant-NLGridWatch-feed-watcher"}
TIMEOUT = 30

# Sample location: Dam, 1012JS Amsterdam.
SAMPLE_POSTCODE = "1012JS"
SAMPLE_LAT, SAMPLE_LON = 52.3729, 4.8941

PDOK_URL = "https://api.pdok.nl/bzk/locatieserver/search/v3_1/free"
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
CAPACITY_BASE = "https://services.arcgis.com/nSZVuSZjHpEZZbRo/ArcGIS/rest/services"
CAPACITY_LAYERS = {
    "afname": f"{CAPACITY_BASE}/Capaciteitskaart_elektriciteitsnet_v2_afname/FeatureServer/0/query",
    "teruglevering": f"{CAPACITY_BASE}/Capaciteitskaart_elektriciteitsnet_v2_teruglevering/FeatureServer/0/query",
}
EO_BASE = "https://energieonderbrekingen.nl"
CAPACITY_REQUIRED = {
    "afname": ["afname", "voedingsgebied_naam", "voedingsgebied_id", "RNB",
               "wachtrij_afname", "unieke_verzoeken_afname"],
    "teruglevering": ["opwek", "voedingsgebied_naam", "voedingsgebied_id", "RNB",
                      "wachtrij_invoeding", "unieke_verzoeken_invoeding"],
}
KNOWN_STATUS_CODES = {0, 1, 2, 3}
METEO_HOURLY = ["time", "temperature_2m", "cloud_cover", "shortwave_radiation"]
POINT_RE = re.compile(r"POINT\(([0-9.]+)\s+([0-9.]+)\)")


def _get(url: str, **params):
    return requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)


def _fail(resp_or_exc) -> dict:
    """Classify a failed request; 404/410 count as 'gone', the rest transient."""
    if isinstance(resp_or_exc, requests.Response):
        code = resp_or_exc.status_code
        return {"reachable": code not in (404, 410), "http": code, "transient": code >= 500 or code == 429}
    return {"reachable": True, "http": None, "transient": True, "error": type(resp_or_exc).__name__}


def check_pdok() -> dict:
    try:
        resp = _get(PDOK_URL, q=SAMPLE_POSTCODE, fq="type:postcode", rows=1)
    except requests.RequestException as exc:
        return _fail(exc)
    if not resp.ok:
        return _fail(resp)
    docs = resp.json().get("response", {}).get("docs") or []
    doc = docs[0] if docs else {}
    missing = [f"missing field {k}" for k in ("centroide_ll", "weergavenaam") if k not in doc]
    if "centroide_ll" in doc and not POINT_RE.search(doc["centroide_ll"]):
        missing.append("centroide_ll (POINT format)")
    if not docs:
        missing.append("response.docs (no result for sample postcode)")
    return {"reachable": True, "http": resp.status_code, "fields": sorted(doc), "missing": missing}


def check_capacity(layer: str, url: str) -> dict:
    try:
        resp = _get(url, f="json", geometry=f"{SAMPLE_LON},{SAMPLE_LAT}",
                    geometryType="esriGeometryPoint", inSR="4326",
                    spatialRel="esriSpatialRelIntersects", outFields="*",
                    returnGeometry="false")
    except requests.RequestException as exc:
        return _fail(exc)
    if not resp.ok:
        return _fail(resp)
    payload = resp.json()
    if "error" in payload:  # ArcGIS reports errors with HTTP 200
        code = payload["error"].get("code")
        return {"reachable": code not in (400, 404, 410, 499), "http": code,
                "transient": code not in (400, 404, 410, 499),
                "error": str(payload["error"].get("message"))[:200]}
    fields = sorted(f.get("name") for f in payload.get("fields") or [])
    missing = [f"missing field {k}" for k in CAPACITY_REQUIRED[layer] if k not in fields]
    features = payload.get("features") or []
    if not features:
        missing.append("features (sample point no longer intersects a supply area)")
    else:
        code = features[0].get("attributes", {}).get("afname" if layer == "afname" else "opwek")
        if code is not None and code not in KNOWN_STATUS_CODES:
            missing.append(f"status code {code!r} is not in STATUS_LABELS (0-3)")
    return {"reachable": True, "http": resp.status_code, "fields": fields, "missing": missing}


def check_open_meteo() -> dict:
    try:
        resp = _get(OPEN_METEO_URL, latitude=SAMPLE_LAT, longitude=SAMPLE_LON,
                    hourly="temperature_2m,cloud_cover,shortwave_radiation",
                    timezone="Europe/Amsterdam", forecast_days=2)
    except requests.RequestException as exc:
        return _fail(exc)
    if not resp.ok:
        return _fail(resp)
    hourly = resp.json().get("hourly") or {}
    missing = [f"missing field hourly.{k}" for k in METEO_HOURLY if k not in hourly]
    if hourly.get("time") and len(hourly["time"]) < 24:
        missing.append("hourly.time (fewer than 24 rows)")
    return {"reachable": True, "http": resp.status_code, "fields": sorted(hourly), "missing": missing}


def check_eo(path: str, method: str) -> dict:
    """Without credentials we only expect an auth error (401/400), not 404."""
    try:
        resp = requests.request(method, f"{EO_BASE}{path}", headers=HEADERS, timeout=TIMEOUT)
    except requests.RequestException as exc:
        return _fail(exc)
    if resp.status_code in (404, 410) or resp.status_code >= 500:
        return _fail(resp)
    return {"reachable": True, "http": resp.status_code, "missing": []}


def collect() -> dict:
    sources = {"pdok_locatieserver": check_pdok(), "open_meteo": check_open_meteo()}
    for layer, url in CAPACITY_LAYERS.items():
        sources[f"capacity_{layer}"] = check_capacity(layer, url)
    sources["energieonderbrekingen_token"] = check_eo("/oauth/token", "POST")
    sources["energieonderbrekingen_disruptions"] = check_eo("/api/v2/disruptions", "GET")
    return sources


def problems(src: dict) -> list[str]:
    if src.get("transient"):
        return []
    out = list(src.get("missing") or [])
    if not src.get("reachable", True):
        out.append(f"endpoint gone (HTTP {src.get('http')})")
    return out


def llm_summary(report: str) -> str:
    try:
        from openai import OpenAI
    except ImportError:
        return ""
    if os.getenv("XAI_API_KEY"):
        client, model = OpenAI(base_url="https://api.x.ai/v1", api_key=os.environ["XAI_API_KEY"]), "grok-4"
    elif os.getenv("OPENROUTER_API_KEY"):
        client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.environ["OPENROUTER_API_KEY"])
        model = "deepseek/deepseek-v4.1-flash"
    else:
        return ""
    prompt = (
        f"An upstream data source of the Home Assistant integration {COMPONENT} changed. "
        "In 5 bullet points max, explain the likely user impact and which code in api.py "
        f"or coordinator.py needs to change.\n\n{report}"
    )
    try:
        completion = client.chat.completions.create(model=model, messages=[{"role": "user", "content": prompt}])
        return completion.choices[0].message.content or ""
    except Exception as exc:  # noqa: BLE001
        print(f"LLM summary skipped: {exc}")
        return ""


def set_env(**values: str) -> None:
    env_file = os.getenv("GITHUB_ENV")
    if not env_file:
        return
    with open(env_file, "a", encoding="utf-8") as fh:
        for key, value in values.items():
            fh.write(f"{key}={value}\n")


def main() -> int:
    current = collect()
    previous = {}
    if MEMORY_PATH.is_file():
        try:
            previous = json.loads(MEMORY_PATH.read_text(encoding="utf-8"))
        except ValueError:
            previous = {}

    new_problems: dict[str, list[str]] = {}
    for name, src in current.items():
        status = "transient error" if src.get("transient") else ("problem" if problems(src) else "ok")
        print(f"{name:36} HTTP {src.get('http')!s:5} {status}")
        if src.get("transient"):
            # Keep the last good fingerprint; don't overwrite it with noise.
            if name in previous:
                current[name] = previous[name]
            continue
        fresh = [p for p in problems(src) if p not in problems(previous.get(name, {}))]
        if fresh:
            new_problems[name] = fresh
        old_fields = set(previous.get(name, {}).get("fields") or [])
        added = sorted(set(src.get("fields") or []) - old_fields) if old_fields else []
        if added:
            print(f"  new fields (informational): {', '.join(added)}")

    MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    MEMORY_PATH.write_text(json.dumps(current, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if not new_problems:
        print("No breaking upstream changes.")
        return 0

    lines = ["## Upstream change detected", "",
             f"The daily feed watcher found breaking changes in a source used by `{COMPONENT}`.", ""]
    for name, items in new_problems.items():
        lines.append(f"### `{name}`")
        lines += [f"- {item}" for item in items]
        lines.append("")
    report = "\n".join(lines)
    summary = llm_summary(report)
    if summary:
        report += "\n### AI impact summary\n\n" + summary + "\n"
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(report)
    set_env(SCHEMA_CHANGED="true",
            ISSUE_TITLE=f"Upstream change: {', '.join(sorted(new_problems))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
