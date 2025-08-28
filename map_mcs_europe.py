import json
import time
from pathlib import Path
from typing import Dict, List

import folium
from folium.plugins import MarkerCluster
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

BASE_DIR = Path(__file__).parent
DATA_PATH = BASE_DIR / "data" / "mcs_europe_seed.json"
OUTPUT_DIR = BASE_DIR / "output"
GEOJSON_PATH = OUTPUT_DIR / "mcs_europe.geojson"
MAP_HTML_PATH = OUTPUT_DIR / "mcs_europe_map.html"


def load_sites() -> List[Dict]:
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def geocode_sites(sites: List[Dict]) -> List[Dict]:
    geolocator = Nominatim(user_agent="mcs-locator-eu")
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1.1, max_retries=3, error_wait_seconds=2.0)

    enriched: List[Dict] = []
    for site in sites:
        query = f"{site['city']}, {site['country']}"
        try:
            location = geocode(query)
        except Exception:
            location = None
        if location is None:
            # Attempt operator and name hints
            alt_query = f"{site['name']}, {site['city']}, {site['country']}"
            try:
                location = geocode(alt_query)
            except Exception:
                location = None
        if location is None:
            print(f"[WARN] Could not geocode: {query}")
            continue
        enriched.append({
            **site,
            "latitude": location.latitude,
            "longitude": location.longitude,
        })
        time.sleep(0.2)
    return enriched


def to_geojson(features: List[Dict]) -> Dict:
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [f["longitude"], f["latitude"]]},
                "properties": {
                    "name": f["name"],
                    "city": f["city"],
                    "country": f["country"],
                    "operator": f["operator"],
                    "status": f["status"],
                    "source": f["source"],
                },
            }
            for f in features
        ],
    }


def make_map(features: List[Dict]) -> folium.Map:
    # Center roughly on Europe
    m = folium.Map(location=[51.1657, 10.4515], zoom_start=5, tiles="CartoDB positron")
    cluster = MarkerCluster().add_to(m)

    status_to_color = {
        "live": "green",
        "pilot": "orange",
        "announced": "blue",
    }

    for f in features:
        color = status_to_color.get(f.get("status", "announced"), "blue")
        popup_html = f"""
        <b>{f['name']}</b><br/>
        {f['city']}, {f['country']}<br/>
        Operator: {f['operator']}<br/>
        Status: {f['status']}<br/>
        <a href=\"{f['source']}\" target=\"_blank\">Source</a>
        """.strip()
        folium.CircleMarker(
            location=[f["latitude"], f["longitude"]],
            radius=7,
            color=color,
            fill=True,
            fill_opacity=0.8,
            popup=folium.Popup(popup_html, max_width=300),
        ).add_to(cluster)

    return m


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    sites = load_sites()
    enriched = geocode_sites(sites)

    geojson = to_geojson(enriched)
    with open(GEOJSON_PATH, "w", encoding="utf-8") as f:
        json.dump(geojson, f, ensure_ascii=False, indent=2)

    m = make_map(enriched)
    m.save(str(MAP_HTML_PATH))
    print(f"Saved GeoJSON to {GEOJSON_PATH}")
    print(f"Saved map to {MAP_HTML_PATH}")


if __name__ == "__main__":
    main()

