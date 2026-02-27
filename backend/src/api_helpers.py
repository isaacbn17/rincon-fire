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

def get_station_list(limit: int = 200) -> Optional[List[str]]:
    """Return a list of station IDs (URLs) from /stations. Limit keeps it reasonable."""
    url = f"{BASE}/stations"
    resp = _get(url, params={"limit": limit})
    if not resp:
        return None
    try:
        data = resp.json()
        out = []
        for feat in data.get("features", []):
            sid = feat.get("id")
            if sid:
                out.append(sid)
        return out
    except Exception as e:
        print(f"[ERR] parsing stations: {e}")
        return None

def request_observations(station_id_url: str, latest_only: bool = True) -> Optional[Dict[str, Any]]:
    """Fetch observations for a station URL (e.g., 'https://api.weather.gov/stations/KDCA')."""
    url = station_id_url.rstrip("/") + ("/observations/latest" if latest_only else "/observations")
    resp = _get(url)
    return resp.json() if resp else None

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
                has_next_page = False

        except Exception as e:
            print(f"[ERR] parsing stations: {e}")
            return None
    return out


def request_seven_day_weather(lat: float, lon: float):
    points_url = f"{BASE}/points/{lat},{lon}"
    resp = _get(points_url)
    if not resp:
        return None
    try:
        points = resp.json()
        stations_url = points.get("properties", {}).get("observationStations")
        if not stations_url:
            print("[WARN] No observationStations link in points payload.")
            return None
    except Exception as e:
        print(f"[ERR] parsing points: {e}")
        return None

    resp2 = _get(stations_url)
    if not resp2:
        return None
    try:
        stations_payload = resp2.json()
        features = stations_payload.get("features", [])
        if not features:
            print("[WARN] No stations found near the provided coordinates.")
            return None
        first_station = features[0].get("id")
        if not first_station:
            print("[WARN] First station has no id.")
            return None
    except Exception as e:
        print(f"[ERR] parsing stations list for point: {e}")
        return None

    # Iterate through pages and then grab only dates/times that we want
    out = []
    has_next_page = True
    url = first_station.rstrip("/") + "/observations"
    hour = -1
    minutes = -1
    while has_next_page and len(out) < 7:
        resp = _get(url, params={"limit": 500})
        if not resp:
            return None
        try:
            data = resp.json()
            for item in data['features']:
                sid = item["id"]
                timestamp = item['properties']['timestamp']
                date_time = datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S+00:00')
                if hour == -1:
                    hour = date_time.hour
                    minutes = date_time.minute

                if date_time.hour == hour and date_time.minute == minutes:
                    out.append(item['properties'])
                    if len(out) >= 7:
                        break

            if 'pagination' in data.keys():
                url = data['pagination']['next']
                has_next_page = True
            else:
                has_next_page = False

        except Exception as e:
            print(f"[ERR] parsing stations: {e}")
            return None
    return out

def extract_weather(weather_data):
    extracted_weather_data = []
    for observation in weather_data:
        properties = observation
        extracted_weather_data.append({
            'date': properties.get('timestamp'),
            'temperature': properties.get('temperature', {}).get('value'),
            'dewpoint': properties.get('dewpoint', {}).get('value'),
            'relativeHumidity': properties.get('relativeHumidity', {}).get('value'),
            'precipitationLast3Hours': properties.get('precipitationLast3Hours', {}).get('value'),
            'windDirection': properties.get('windDirection', {}).get('value'),
            'windSpeed': properties.get('windSpeed', {}).get('value'),
            'windGust': properties.get('windGust', {}).get('value'),
            'barometricPressure': properties.get('barometricPressure', {}).get('value'),
        })

    weather_df = pd.DataFrame(extracted_weather_data)
    weather_df['date'] = pd.to_datetime(weather_df['date']).dt.strftime('%Y-%m-%d')

    return weather_df

def get_formatted_weather_data(station_url: str):
    weather_data = request_seven_day_observations(station_url)
    # print(weather_data)
    weather_data = extract_weather(weather_data)

    date = weather_data.iloc[0]['date']
    weather_row = pd.Series([])

    weather_data = weather_data.drop('date', axis=1)

    for i, weather_day in weather_data.iterrows():
        weather_row = pd.concat([weather_day, weather_row])

    # weather_row = pd.concat([pd.Series([date]), weather_row])

    cols = ['temperature', 'dewpoint', 'relative_humidity', 'precipitation', 'wind_direction', 'wind_speed',
            'wind_gust', 'air_pressure']

    final_cols = []
    for i in range(1, 8):
        for col in cols:
            final_cols.append(col + '_' + str(i))
    weather_row = weather_row.to_numpy()
    formatted_data_df = pd.DataFrame([weather_row], columns=final_cols)
    return formatted_data_df


def get_all_station_observations(station_id_list: List[str], latest_only: bool = True) -> Dict[str, Dict[str, Any]]:
    """Loop over station IDs and collect observations."""
    out: Dict[str, Dict[str, Any]] = {}
    for sid in station_id_list:
        obs = request_observations(sid, latest_only=latest_only)
        if obs is not None:
            out[sid] = obs
        else:
            print("Hit a transient error; sleeping 2s...")
            time.sleep(2)
    return out

def request_weather(lat: float, lon: float) -> Optional[Dict[str, Any]]:
    """
    Given a latitude/longitude, use /points to find nearby stations and return
    the latest observation from the first available station.
    """
    points_url = f"{BASE}/points/{lat},{lon}"
    resp = _get(points_url)
    if not resp:
        return None
    try:
        points = resp.json()
        stations_url = points.get("properties", {}).get("observationStations")
        if not stations_url:
            print("[WARN] No observationStations link in points payload.")
            return None
    except Exception as e:
        print(f"[ERR] parsing points: {e}")
        return None

    resp2 = _get(stations_url)
    if not resp2:
        return None
    try:
        stations_payload = resp2.json()
        features = stations_payload.get("features", [])
        if not features:
            print("[WARN] No stations found near the provided coordinates.")
            return None
        first_station = features[0].get("id")
        if not first_station:
            print("[WARN] First station has no id.")
            return None
    except Exception as e:
        print(f"[ERR] parsing stations list for point: {e}")
        return None

    latest = request_observations(first_station, latest_only=True)
    return latest


def save_station_list(limit: int = 500) -> Optional[List[str]]:
    """Return a list of station IDs (URLs) from /stations. Limit keeps it reasonable."""
    url = f"{BASE}/stations"
    has_next_page = True

    out = []
    prev_out = -1
    while has_next_page:
        resp = _get(url, params={"limit": limit})
        if not resp:
            output = pd.DataFrame(out, columns=['station_url', 'latitude', 'longitude'])
            output.to_csv('weather_stations.csv')
            return None
        try:
            data = resp.json()
            for item in data['features']:
                sid = item["id"]
                coordinates = item["geometry"]["coordinates"]
                out.append([sid, coordinates[1], coordinates[0]])
            if data['pagination'] is not None:
                url = data['pagination']['next']
                has_next_page = True
            else:
                has_next_page = False

        except Exception as e:
            print(f"[ERR] parsing stations: {e}")
            return None

        if len(out) == prev_out:
            has_next_page = False
        prev_out = len(out)

    output = pd.DataFrame(out, columns=['station_url', 'latitude', 'longitude'])
    print(len(output))
    output.to_csv('weather_stations.csv')

