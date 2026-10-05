#!/usr/bin/env python3
"""Watch Open-Meteo demo feed for schema drift (AI summariser)."""
from __future__ import annotations

import os

import requests
from openai import OpenAI

COMPONENT = "custom_components/starter_feed/"
FEED_SAMPLE = (
    "https://api.open-meteo.com/v1/forecast"
    "?latitude=52.37&longitude=4.89"
    "&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m"
    "&hourly=temperature_2m,weather_code"
    "&forecast_days=1&timezone=Europe/Amsterdam"
)
MEMORY_PATH = ".memory/starter_feed_schema.json"


def _llm_client():
    xai = os.getenv("XAI_API_KEY")
    if xai:
        return OpenAI(base_url="https://api.x.ai/v1", api_key=xai), "grok-4"
    or_key = os.getenv("OPENROUTER_API_KEY")
    if or_key:
        return (
            OpenAI(base_url="https://openrouter.ai/api/v1", api_key=or_key),
            "deepseek/deepseek-v4.1-flash",
        )
    print("No XAI_API_KEY or OPENROUTER_API_KEY — exiting cleanly.")
    raise SystemExit(0)


headers = {"User-Agent": "HomeAssistant-StarterFeed/0.1.0-feed-watcher"}
snippet = ""
try:
    resp = requests.get(FEED_SAMPLE, headers=headers, timeout=30)
    snippet = resp.text[:3000]
    print(f"Feed HTTP {resp.status_code}, bytes={len(resp.content)}")
except Exception as exc:  # noqa: BLE001
    print(f"Feed fetch failed: {exc}")
    raise SystemExit(0)

client, model = _llm_client()
memory = ""
if os.path.isfile(MEMORY_PATH):
    with open(MEMORY_PATH, encoding="utf-8") as fh:
        memory = fh.read()[:2000]

prompt = f"""
Compare this live Open-Meteo JSON snippet to the remembered schema.
Flag breaking field changes relevant to {COMPONENT}.

SCHEMA MEMORY:
{memory}

LIVE SNIPPET:
{snippet}
"""
try:
    completion = client.chat.completions.create(
        model=model, messages=[{"role": "user", "content": prompt}]
    )
    report = completion.choices[0].message.content or ""
    print(report)
    with open("feed_watch_report.md", "w", encoding="utf-8") as fh:
        fh.write(report)
except Exception as exc:  # noqa: BLE001
    print(f"feed_watcher failed: {exc}")
