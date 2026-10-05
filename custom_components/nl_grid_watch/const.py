"""Constants for the NL Grid Watch integration."""

DOMAIN = "nl_grid_watch"
NAME = "NL Grid Watch"
VERSION = "0.1.3"

PLATFORMS = ["sensor", "binary_sensor"]

CONF_POSTAL_CODE = "postal_code"
CONF_CLIENT_ID = "client_id"
CONF_CLIENT_SECRET = "client_secret"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_SCAN_INTERVAL = 30

PDOK_URL = "https://api.pdok.nl/bzk/locatieserver/search/v3_1/free"
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
CAPACITY_BASE = "https://services.arcgis.com/nSZVuSZjHpEZZbRo/ArcGIS/rest/services"
CAPACITY_LAYERS = {
    "afname": f"{CAPACITY_BASE}/Capaciteitskaart_elektriciteitsnet_v2_afname/FeatureServer/0/query",
    "teruglevering": (
        f"{CAPACITY_BASE}/Capaciteitskaart_elektriciteitsnet_v2_teruglevering/FeatureServer/0/query"
    ),
}
EO_BASE = "https://energieonderbrekingen.nl"
EO_TOKEN_URL = f"{EO_BASE}/oauth/token"
EO_DISRUPTIONS_URL = f"{EO_BASE}/api/v2/disruptions"

STATUS_LABELS = {
    0: "available",
    1: "limited",
    2: "investigation",
    3: "queue",
}

BACKFEED_HOURS = range(10, 16)
EVENING_HOURS = range(16, 22)
SOLAR_HIGH = 500
SOLAR_LOW = 300
CLOUD_CLEAR = 40
CLOUD_DARK = 70
COLD_EVENING = 8
