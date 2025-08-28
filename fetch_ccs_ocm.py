import os
import time
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

import requests
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_PATH = OUTPUT_DIR / "ccs_europe.geojson"

# ISO country codes for Europe (non-exhaustive but broad). Adjust as needed.
EUROPE_ISO = [
    "AL","AD","AT","BE","BA","BG","HR","CY","CZ","DK","EE","FI","FR","DE","GR","HU",
    "IS","IE","IT","XK","LV","LI","LT","LU","MT","MD","MC","ME","NL","MK","NO","PL",
    "PT","RO","SM","RS","SK","SI","ES","SE","CH","GB","UA","BY","TR"
]

# OCM connection type ID for CCS (Combo 2 / Type 2 CCS)
OCM_CCS2_ID = 32

API_URL = "https://api.openchargemap.io/v3/poi/"
PAGE_SIZE = 1000
SLEEP_SECONDS = 1.2  # polite delay between requests


def fetch_country_ccs(country_code: str, api_key: Optional[str]) -> List[Dict[str, Any]]:
    params: Dict[str, Any] = {
        "output": "json",
        "countrycode": country_code,
        "connectiontypeid": OCM_CCS2_ID,
        "minpowerkw": 50,
        "maxresults": PAGE_SIZE,
        "compact": True,
        "verbose": False,
    }
    if api_key:
        params["key"] = api_key

    all_items: List[Dict[str, Any]] = []
    offset = 0
    while True:
        params["offset"] = offset
        resp = requests.get(API_URL, params=params, timeout=60)
        if resp.status_code != 200:
            print(f"[WARN] {country_code} request failed: {resp.status_code} {resp.text[:200]}")
            break
        batch = resp.json()
        if not batch:
            break
        all_items.extend(batch)
        print(f"{country_code}: fetched {len(batch)} (total {len(all_items)})")
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
        time.sleep(SLEEP_SECONDS)
    return all_items


def transform_to_geojson(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    features: List[Dict[str, Any]] = []
    for it in items:
        addr = it.get("AddressInfo") or {}
        op = it.get("OperatorInfo") or {}
        lat = addr.get("Latitude")
        lon = addr.get("Longitude")
        if lat is None or lon is None:
            continue
        feature = {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": {
                "name": addr.get("Title") or "CCS Charger",
                "city": addr.get("Town") or "",
                "country": (addr.get("Country") or {}).get("ISOCode") or "",
                "operator": (op.get("Title") if isinstance(op, dict) else "") or "",
                "status": "fast",
                "source": f"https://openchargemap.org/site/poi/{it.get('ID')}",
                "siteType": "CCS"
            },
        }
        features.append(feature)
    return {"type": "FeatureCollection", "features": features}


def main() -> None:
    load_dotenv()
    api_key = os.getenv("OCM_API_KEY")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    all_items: List[Dict[str, Any]] = []
    for cc in EUROPE_ISO:
        try:
            items = fetch_country_ccs(cc, api_key)
            all_items.extend(items)
        except Exception as e:
            print(f"[ERROR] Failed for {cc}: {e}")
        time.sleep(SLEEP_SECONDS)

    geojson = transform_to_geojson(all_items)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(geojson, f, ensure_ascii=False, indent=2)
    print(f"Saved CCS GeoJSON to {OUTPUT_PATH} with {len(geojson['features'])} features")


if __name__ == "__main__":
    main()
