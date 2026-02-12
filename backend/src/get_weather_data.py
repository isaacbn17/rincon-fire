from urllib.error import URLError
from meteostat import Point, hourly
import pandas as pd
from datetime import timedelta
from pathlib import Path


WEATHER_VARS = [
    "temp",   # temperature (°C)
    "dwpt",   # dewpoint (°C)
    "rhum",   # relativeHumidity (%)
    "prcp",   # precipitation (mm) -- Meteostat is usually per hour
    "wdir",   # windDirection (deg)
    "wspd",   # windSpeed (km/h)
    "wpgt",   # windGust (km/h)
    "pres",   # barometricPressure (hPa)
]

# Map Meteostat column names -> your desired names
RENAME = {
    "temp": "temperature",
    "dwpt": "dewpoint",
    "rhum": "relativeHumidity",
    "prcp": "precipitationLast3Hours",   # NOTE: see comment below
    "wdir": "windDirection",
    "wspd": "windSpeed",
    "wpgt": "windGust",
    "pres": "barometricPressure",
}


def _fetch_7days_same_hour(lat: float, lon: float, end_dt: pd.Timestamp) -> pd.DataFrame:
    """
    Fetch hourly data from Meteostat for the 7 days ending at end_dt,
    then keep only rows matching end_dt.hour, and return exactly 7 rows
    (with NaNs if missing).
    """
    start_dt = end_dt - timedelta(days=6)
    loc = Point(lat, lon)

    # Fetch hourly range
    weather = hourly(loc, start_dt.to_pydatetime(), end_dt.to_pydatetime()).fetch()

    if weather is None or len(weather) == 0:
        # Return empty; caller decides what to do
        return pd.DataFrame()

    # Keep only the hour-of-day matching discovery hour
    hour = end_dt.hour
    weather = weather.loc[weather.index.hour == hour, WEATHER_VARS].copy()

    # Build an expected 7-day date index at that hour (one per day)
    expected = pd.date_range(
        start=start_dt.normalize() + pd.Timedelta(hours=hour),
        end=end_dt.normalize() + pd.Timedelta(hours=hour),
        freq="D",
    )

    # Reindex so we always have 7 rows (NaNs if Meteostat missing)
    weather = weather.reindex(expected)

    # Rename to your schema and return
    weather = weather.rename(columns=RENAME)
    weather.index.name = "date_time"
    return weather.reset_index()


def _weather_to_wide(weather7: pd.DataFrame) -> dict:
    """
    Convert a 7-row dataframe into wide columns like:
    temperature_d1 ... temperature_d7, etc.
    d1 = most recent (fire date), d7 = oldest (6 days before)
    """
    out = {}

    if weather7.empty:
        # Fill all weather columns with NaN
        for base in RENAME.values():
            for d in range(1, 8):
                out[f"{base}_d{d}"] = pd.NA
        return out

    # Ensure sorted oldest->newest then label d7..d1 OR easiest: d1=newest
    weather7 = weather7.sort_values("date_time")  # oldest -> newest

    # Map row positions to d7..d1, but you asked 7 days leading up; most people prefer d1 = fire day.
    # So: oldest -> d7, newest -> d1
    for idx, row in weather7.iterrows():
        # idx 0 oldest -> d7, idx 6 newest -> d1
        d = 7 - idx
        for col in RENAME.values():
            out[f"{col}_d{d}"] = row[col]

    return out


def build_rows_for_fire(
    object_id,
    discovery_dt: pd.Timestamp,
    lat: float,
    lon: float,
    include_previous_year_control: bool = True,
) -> list[dict]:
    """
    Returns a list of row dicts: [fire_row] plus optionally [control_row].
    """
    rows = []

    # Fire row (fire_presence = 1)
    w7 = _fetch_7days_same_hour(lat, lon, discovery_dt)
    row_fire = {
        "OBJECTID": object_id,
        "date_time": discovery_dt,
        "latitude": lat,
        "longitude": lon,
        "fire_presence": 1,
        **_weather_to_wide(w7),
    }
    rows.append(row_fire)

    if include_previous_year_control:
        # Control row: same location, same 7-day window, 1 year earlier (fire_presence = 0)
        control_dt = discovery_dt - pd.Timedelta(days=365)
        w7c = _fetch_7days_same_hour(lat, lon, control_dt)
        row_ctrl = {
            "OBJECTID": object_id,
            "date_time": control_dt,
            "latitude": lat,
            "longitude": lon,
            "fire_presence": 0,
            **_weather_to_wide(w7c),
        }
        rows.append(row_ctrl)

    return rows


if __name__ == "__main__":
    base_dir = Path.cwd()
    in_path = base_dir / ".." / "data" / "fires_utah.csv"
    out_path = base_dir / ".." / "data" / "fires_utah_week_wide.csv"

    fires = pd.read_csv(in_path)

    # Parse "6/27/2020 18:51" safely
    fires["attr_FireDiscoveryDateTime"] = pd.to_datetime(
        fires["attr_FireDiscoveryDateTime"], errors="coerce"
    )

    rows_out = []
    for i, r in fires.iterrows():
        try:
            dt = r["attr_FireDiscoveryDateTime"]
            if pd.isna(dt):
                continue

            lat = float(r["attr_InitialLatitude"])
            lon = float(r["attr_InitialLongitude"])
            object_id = r.get("OBJECTID", i)

            rows_out.extend(
                build_rows_for_fire(
                    object_id=object_id,
                    discovery_dt=dt,
                    lat=lat,
                    lon=lon,
                    include_previous_year_control=True,  # set False if you only want fire rows
                )
            )

            if i % 100 == 0:
                print(f"Processed {i}/{len(fires)}")

        except URLError as e:
            print(e)
            break
        except Exception as e:
            # Keep going on bad rows
            print(f"Row {i} skipped: {e}")

    out_df = pd.DataFrame(rows_out)
    out_df.to_csv(out_path, index=False)
    print(f"Wrote: {out_path}")
