import requests
import time
from typing import Any, Dict, List, Optional
import pandas as pd
from datetime import datetime

USER_AGENT = "RinconFire/1.0 (contact: user)"  # set a real contact if you can
DEFAULT_TIMEOUT = 15  # seconds
BASE = "https://api.weather.gov"

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
            return resp
        except requests.RequestException as e:
            wait = backoff ** attempt
            print(f"[EXC] {e}; retrying in {wait:.1f}s...")
            time.sleep(wait)

    print(f"[ERR] Max retries exceeded for {url}")
    return None

def request_seven_day_observations(station_id_url: str):
    # Iterate through pages and then grab only dates/times that we want
    out = []
    has_next_page = True
    url = station_id_url.rstrip("/") + "/observations"
    hour = -1
    days = []
    while has_next_page and len(out) < 7:
        resp = _get(url, params={"limit": 500})
        if not resp:
            print("No response")
            return None
        try:
            data = resp.json()
            for item in data['features']:
                sid = item["id"]
                timestamp = item['properties']['timestamp']
                date_time = datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S+00:00')
                if hour == -1:
                    hour = date_time.hour

                if date_time.hour == hour and date_time.day not in days:
                    out.append(item['properties'])
                    days.append(date_time.day)
                    if len(out) >= 7:
                        break

            if 'pagination' in data.keys():
                url = data['pagination']['next']
                has_next_page = True
            else:
                print("No next page")
                has_next_page = False

        except Exception as e:
            print(f"[ERR] parsing stations: {e}")
            return None
    return out

weather_station_url = "https://api.weather.gov/stations/KAGU1"
weather_data = request_seven_day_observations(weather_station_url)

print(weather_data)
