import csv
import math
import time
from pathlib import Path
from pprint import pprint
from typing import Any, Dict, List, Optional

import requests

from config import Config

USER_AGENT = "RinconFire/1.0 (contact: youremail@example.com)"  # set a real contact if you can
DEFAULT_TIMEOUT = 15  # seconds
BASE = "https://api.weather.gov"
WEATHER_STATIONS_CSV = Config().STATIONS_DIR

def _get(url: str, *, headers: Optional[Dict[str, str]] = None, params: Optional[Dict[str, Any]] = None,
         timeout: int = DEFAULT_TIMEOUT, max_retries: int = 3, backoff: float = 1.5) -> Optional[requests.Response]:
    hdrs = {
        "User-Agent": USER_AGENT,
        "Accept": "application/geo+json"
    }
    if headers:
        hdrs.update(headers)

    for attempt in range(max_retries):
        try:
            resp = requests.get(url, headers=hdrs, params=params, timeout=timeout)
            if resp.status_code == 429 or 500 <= resp.status_code < 600:
                wait = backoff ** attempt
                print(f"[{resp.status_code}] Retrying {url} in {wait:.1f}s...")
                time.sleep(wait)
                continue
            if not resp.ok:
                print(f"[{resp.status_code}] GET {url} failed: {resp.text[:200]}")
                return None
            return resp.json()
        except requests.RequestException as e:
            wait = backoff ** attempt
            print(f"[EXC] {e}; retrying in {wait:.1f}s...")
            time.sleep(wait)

    print(f"[ERR] Max retries exceeded for {url}")
    return None

def simplify_weather_json(weather_json: dict, latitude: float, longitude: float) -> dict:
    props = weather_json.get("properties", {})
    station_name = props.get("stationName", "Unknown Station")

    simplified = {'stationName': station_name, 'latitude': latitude, 'longitude': longitude}
    for key, value in props.items():
        # Skip metadata and URLs
        if key in {"@id", "@type", "icon", "rawMessage", "station", "stationId", "stationName", "textDescription"}:
            continue

        # If the value is a dict with a 'value' field, use that
        if isinstance(value, dict) and "value" in value:
            simplified[key] = value["value"]

        # If it's a list (e.g., cloudLayers), extract first base value or None
        elif isinstance(value, list):
            if len(value) > 0:
                first = value[0]
                if isinstance(first, dict) and "base" in first:
                    simplified[key] = first["base"].get("value")
                else:
                    simplified[key] = None
            else:
                simplified[key] = None
        else:
            simplified[key] = value

    return simplified

def load_weather_stations(n: int) -> List[Dict[str, Any]]:

    """
    Read the first n stations from weather_stations.csv.

    Returns a list of dictionaries:
    {
        "id": int,
        "station_url": str,
        "longitude": float,
        "latitude": float
    }
    """
    if n <= 0:
        raise ValueError("n must be a positive integer")

    stations = []

    with WEATHER_STATIONS_CSV.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i >= n:
                break

            stations.append({
                "id": int(row["id"]),
                "station_url": row["station_url"],
                "longitude": float(row["longitude"]),
                "latitude": float(row["latitude"]),
            })

    return stations

def get_weather_for_stations(n_stations: int):

    stations = load_weather_stations(n_stations)

    weather_records = []
    for station in stations:
        try:
            # Fetch observations for a station URL (e.g., 'https://api.weather.gov/stations/KDCA')
            url = station["station_url"].rstrip("/") + "/observations/latest"
            weather_json = _get(url)
            weather = simplify_weather_json(weather_json, float(station["latitude"]), float(station["longitude"]))
            weather_records.append({
                "station_url": station["station_url"],
                "weather": weather,
                "latitude": station["latitude"],
                "longitude": station["longitude"]
            })

        except Exception as e:
            print(f"Error processing station: {e}")
            continue

    return weather_records

def safe_float(value: Any) -> float:
    if value is None:
        return math.nan
    return float(value)

def weather_to_features(weather_record: dict[str, Any]) -> list[float]:
    """
    Convert a weather.gov observation into the 8 features the RF model expects.
    Order must match training: temperature, dewpoint, humidity, precipitationLast3Hours,
    windDirection, windSpeed, windGust, barometricPressure.
    """
    return [
        safe_float(weather_record.get("temperature")),
        safe_float(weather_record.get("dewpoint")),
        safe_float(weather_record.get("relativeHumidity")),          # humidity
        safe_float(weather_record.get("precipitationLast3Hours")),
        safe_float(weather_record.get("windDirection")),
        safe_float(weather_record.get("windSpeed")),
        safe_float(weather_record.get("windGust")),
        safe_float(weather_record.get("barometricPressure")),
    ]

def practice():
    url = "https://api.weather.gov/stations/0007W/observations/latest"
    weather_json = _get(url)
    weather = simplify_weather_json(weather_json, 30.53099, -84.1787)
    pprint(weather)

if __name__ == "__main__":
    practice()
