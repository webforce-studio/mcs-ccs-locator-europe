# MCS / CCS Locator (Europe)

Static web app to view Megawatt Charging System (MCS) sites and CCS fast chargers (≥50 kW).

## Quick start

1. Create and activate the venv:
   ```bash
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Generate the MCS map and GeoJSON (already provided):
   ```bash
   python map_mcs_europe.py
   ```
3. Start static server:
   ```bash
   python3 -m http.server 8000 -d output
   ```
4. Open `http://localhost:8000/index.html`.

## CCS data options

### Option A: Open Charge Map API (recommended long-term)
- Get API key: https://openchargemap.org/site/develop/api
- Create `.env` at project root:
  ```env
  OCM_API_KEY=YOUR_KEY
  ```
- Fetch CCS ≥50 kW across Europe:
  ```bash
  python fetch_ccs_ocm.py
  ```
- Output written to `output/ccs_europe.geojson`.

### Option B: Manual National Access Point (NAP) import (no API)
- Drop CSV or (Geo)JSON files into `data/nap_raw/`.
- The importer looks for fields (case-insensitive):
  - Connectors: `connector, connectors, socket, plug` containing CCS keywords
  - Power: `power, max_power, max_power_kw, kw` (filter ≥50)
  - Lat/Lon: `lat, latitude` and `lon, lng, longitude`
- Run importer:
  ```bash
  python nap_importer.py
  ```
- Output written to `output/ccs_europe.geojson`.

## Web app
- MapLibre map with sidebar cards and filters.
- Toggles for MCS and CCS in the left sidebar.
- If MapLibre is blocked, the app falls back to an embedded map and opens OSM per-card.
