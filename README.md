<div align="center">

# ⚡ NL Grid Watch
**A Dutch grid-stress forecast for Home Assistant. Backfeed risk when the sun is up. Evening-peak risk when it is not.**

> This is not a cable-fault predictor. It forecasts the two windows where a full voedingsgebied is most likely to be stressed: too much solar teruglevering, or too much evening afname.

[![License](https://img.shields.io/github/license/DonTranQuiL/NL-Grid-Watch-For-Home-assistant?style=for-the-badge&color=007ec6)](https://github.com/DonTranQuiL/NL-Grid-Watch-For-Home-assistant/blob/main/LICENSE)
[![HACS Validation](https://img.shields.io/github/actions/workflow/status/DonTranQuiL/NL-Grid-Watch-For-Home-assistant/hacs.yaml?style=for-the-badge&label=HACS%20VALIDATION&color=5dbb0f)](https://github.com/DonTranQuiL/NL-Grid-Watch-For-Home-assistant/actions)
[![hassfest](https://img.shields.io/github/actions/workflow/status/DonTranQuiL/NL-Grid-Watch-For-Home-assistant/hassfest.yaml?style=for-the-badge&label=HASSFEST&color=5dbb0f)](https://github.com/DonTranQuiL/NL-Grid-Watch-For-Home-assistant/actions)
[![HACS Custom](https://img.shields.io/badge/HACS-CUSTOM-ff6e27?style=for-the-badge)](https://hacs.xyz/)
[![Home Assistant Version](https://img.shields.io/badge/Home%20Assistant-2025.1%2B-007ec6?style=for-the-badge)](https://www.home-assistant.io/)
[![Maintainer](https://img.shields.io/badge/maintainer-%40DonTranQuiL-007ec6?style=for-the-badge)](https://github.com/DonTranQuiL)
[![Donate](https://img.shields.io/badge/buy%20me%20a%20coffee-donate-ffdd00?style=for-the-badge)](https://ko-fi.com/DonTranQuiL)

</div>

### 🚀 What this integration does
NL Grid Watch turns a Dutch postcode into a local overload forecast. Same idea as a weather forecast: not a promise that the fuse will blow, a window where the street cable is most likely to be stressed.

Two directions, same cable:

* **Backfeed, sun up.** Area already tight on teruglevering, and tomorrow is a clear midday. Typical result is inverter trip. A real outage is the failure case.
* **Demand, sun down.** Area already tight on afname, and the coming evening is dark and cold. This is the 16:00–21:00 peak: cooking, heat pumps, EV chargers.

Cable faults and planned work are extra data, not the forecast. Those come from energieonderbrekingen.nl only if you have an API token.

---

## 📥 How to Install (via HACS)

The integration code is not in this repo yet. The repository is the home for it, matching the SkyRadar Fusion layout. Install steps below apply once the first component release is tagged.

1. Open **HACS** in your sidebar and navigate into the **Integrations** panel.
2. Click the three dots (`...`) located in the upper right quadrant and select **Custom repositories**.
3. Input the repository web link: `https://github.com/DonTranQuiL/NL-Grid-Watch-For-Home-assistant`
4. Set the Category selector dropdown to **Integration** and hit **Add**.
5. Locate the newly added **NL Grid Watch** repository card and hit **Download**.
6. ⚠️ **Restart your Home Assistant instance**.
7. Navigate to **Settings > Devices & Services > Add Integration**, lookup **NL Grid Watch**, and enter your postcode.

---

## 📊 Planned entities

* `sensor.nl_grid_watch_area_afname`: capaciteitskaart status for consumption. Available, limited, or queue.
* `sensor.nl_grid_watch_area_teruglevering`: same map, feed-in direction.
* `sensor.nl_grid_watch_backfeed_risk`: none, low, or high, with the midday window in attributes.
* `sensor.nl_grid_watch_evening_peak_risk`: none, low, or high, with the evening window in attributes.
* `binary_sensor.nl_grid_watch_stress_expected`: on when either risk is high. Attribute says which window.
* Optional, with an energieonderbrekingen token: active interruption and next planned work on your postcode.

EnergyZero and ENTSO-E stay separate. Those integrations already exist. This one only adds the Dutch grid layer.

---

## 🔍 Data sources

* Netbeheer Nederland capaciteitskaart, weekly area colour for afname and teruglevering.
* Open-Meteo hourly forecast at the postcode: irradiance, cloud, temperature.
* Optional: [energieonderbrekingen.nl API v2](https://energieonderbrekingen.nl/api/v2/). OAuth client-credentials, scope `read:disruptions`. Enexis, Liander, Stedin.

The capaciteitskaart is about connections above 3x80A. It does not see your street cabinet. A high risk means "afternoons or evenings like this are when areas like yours get inverter trips or local overload", not "your house goes dark at 16:40".

---

## ⚙️ Status

Repository created from the [SkyRadar Fusion](https://github.com/DonTranQuiL/ADSB-For-Home-assistant) layout. Component code, config flow, and the notification blueprint come next.

## Credits

Capaciteitskaart data is published by Netbeheer Nederland and TenneT. Interruption data, when enabled, is published by Enexis, Liander and Stedin via energieonderbrekingen.nl.
