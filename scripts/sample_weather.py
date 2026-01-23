import time
from pprint import pprint
from typing import Any, Dict, List, Optional
import requests


USER_AGENT = "RinconFire/1.0 (contact: youremail@example.com)"  # set a real contact if you can
DEFAULT_TIMEOUT = 15  # seconds
BASE = "https://api.weather.gov"
# WEATHER_STATIONS_CSV = Config().STATIONS_DIR

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


def practice():
    url = "https://api.weather.gov/stations/0007W/observations/latest"
    weather_json = _get(url)
    weather = simplify_weather_json(weather_json, 30.53099, -84.1787)
    pprint(weather)

if __name__ == "__main__":
    practice()