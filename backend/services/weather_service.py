import time
from datetime import datetime
import pandas as pd
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
            return resp  # .json()
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
    print(weather_data)
    weather_data = extract_weather(weather_data)

    date = weather_data.iloc[0]['date']
    weather_row = pd.Series([])

    weather_data = weather_data.drop('date', axis=1)

    for i, weather_day in weather_data.iterrows():
        weather_row = pd.concat([weather_day, weather_row])

    weather_row = pd.concat([pd.Series([date]), weather_row])

    cols = ['temperature', 'dewpoint', 'relative_humidity', 'precipitation', 'wind_direction', 'wind_speed',
            'wind_gust', 'air_pressure']

    final_cols = ['date_time']
    for i in range(1, 8):
        for col in cols:
            final_cols.append(col + '_' + str(i))
    weather_row = weather_row.to_numpy()
    formatted_data_df = pd.DataFrame([weather_row], columns=final_cols)
    return formatted_data_df

def prepare_weather_week(df):
    # 1. Standardize types and sort to ensure day0 is the oldest, day6 is the newest
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date", ascending=True).reset_index(drop=True)

    # 2. Define the filling logic
    fill_values = {
        "temperature": 22.2,
        "dewpoint": 5.6,
        "relativeHumidity": 39.0,
        "barometricPressure": 1014.9,
        "precipitationLast3Hours": 0,
        "windDirection": 0,
        "windSpeed": 0,
        "windGust": 0
    }

    # 3. Apply the fills (handles None/NaN)
    df = df.fillna(value=fill_values)

    # 4. Define features and pivot
    feature_cols = [
        "temperature", "dewpoint", "relativeHumidity", "precipitationLast3Hours",
        "windDirection", "windSpeed", "windGust", "barometricPressure",
    ]

    # Create week_id (assuming 7 rows = 1 week)
    df["week_id"] = 0

    X_weather = (
        df
        .set_index(["week_id", df.groupby("week_id").cumcount()])
        [feature_cols]
        .unstack()
    )

    # 5. Rename columns to feature_day0, feature_day1...
    X_weather.columns = [
        f"{feature}_day{day}"
        for feature, day in X_weather.columns
    ]

    return X_weather