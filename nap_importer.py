import csv
import json
from pathlib import Path
from typing import Any, Dict, List

BASE_DIR = Path(__file__).parent
RAW_DIR = BASE_DIR / "data" / "nap_raw"
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_PATH = OUTPUT_DIR / "ccs_europe.geojson"

# Heuristics for recognizing CCS connectors and power fields in NAP datasets
CCS_KEYWORDS = ["ccs", "combo", "type 2 combo", "ccs2", "iec 62196-3"]
POWER_FIELDS = ["power", "max_power", "max_power_kw", "rated_power", "rated_power_kw", "kw", "maxkw"]
CONNECTOR_FIELDS = ["connector", "connectors", "connector_type", "socket", "plug", "plug_type"]
LAT_FIELDS = ["lat", "latitude", "y"]
LON_FIELDS = ["lon", "lng", "longitude", "x"]
NAME_FIELDS = ["name", "title", "site_name", "address_title"]
CITY_FIELDS = ["city", "town", "municipality", "place"]
COUNTRY_FIELDS = ["country", "country_code", "iso2", "iso"]
OPERATOR_FIELDS = ["operator", "operator_name", "cpo", "owner", "organisation"]


def is_ccs(value: str) -> bool:
    v = (value or "").lower()
    return any(k in v for k in CCS_KEYWORDS)


def parse_power(val: Any) -> float:
    try:
        s = str(val).lower().replace(",", ".")
        # remove units
        for unit in ["kw", "kW", " kw", " kW"]:
            s = s.replace(unit.lower(), "")
        return float(s)
    except Exception:
        return 0.0


def first_key(d: Dict[str, Any], keys: List[str]) -> Any:
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    # try case-insensitive
    lower = {k.lower(): v for k, v in d.items()}
    for k in keys:
        if k in lower and lower[k] not in (None, ""):
            return lower[k]
    return None


def normalize_record(rec: Dict[str, Any]) -> Dict[str, Any] | None:
    lat = first_key(rec, LAT_FIELDS)
    lon = first_key(rec, LON_FIELDS)
    if lat is None or lon is None:
        return None
    try:
        lat = float(lat)
        lon = float(lon)
    except Exception:
        return None

    # connector check
    connector_val = first_key(rec, CONNECTOR_FIELDS)
    if connector_val is None or not is_ccs(str(connector_val)):
        return None

    # power check
    power_val = first_key(rec, POWER_FIELDS)
    if power_val is None or parse_power(power_val) < 50:
        return None

    name = first_key(rec, NAME_FIELDS) or "CCS Charger"
    city = first_key(rec, CITY_FIELDS) or ""
    country = first_key(rec, COUNTRY_FIELDS) or ""
    operator = first_key(rec, OPERATOR_FIELDS) or ""

    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
        "properties": {
            "name": str(name),
            "city": str(city),
            "country": str(country),
            "operator": str(operator),
            "status": "fast",
            "source": "NAP (manual import)",
            "siteType": "CCS",
        },
    }


def load_csv(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [row for row in reader]


def load_geojson(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    feats = data.get("features", [])
    rows: List[Dict[str, Any]] = []
    for feat in feats:
        props = feat.get("properties", {})
        geom = feat.get("geometry", {})
        if geom and geom.get("type") == "Point":
            coords = geom.get("coordinates") or []
            if len(coords) >= 2:
                lon, lat = coords[0], coords[1]
                # merge lat/lon into props for normalization
                props = dict(props)
                props.setdefault("lat", lat)
                props.setdefault("lon", lon)
                rows.append(props)
    return rows


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    features: List[Dict[str, Any]] = []
    for path in RAW_DIR.glob("**/*"):
        if not path.is_file():
            continue
        if path.suffix.lower() == ".csv":
            try:
                rows = load_csv(path)
            except Exception:
                continue
        elif path.suffix.lower() in (".geojson", ".json"):
            try:
                rows = load_geojson(path)
            except Exception:
                continue
        else:
            continue

        for row in rows:
            feat = normalize_record(row)
            if feat:
                features.append(feat)

    fc = {"type": "FeatureCollection", "features": features}
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(fc, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(features)} CCS features to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
