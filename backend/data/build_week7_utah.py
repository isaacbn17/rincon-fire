import pandas as pd
import requests
from datetime import timedelta

# -----------------------------------
# Open-Meteo historical weather
# -----------------------------------
def fetch_daily_weather(lat, lon, start_date, end_date):

    url = "https://archive-api.open-meteo.com/v1/archive"

    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": str(start_date),
        "end_date": str(end_date),
        "daily": [
            "temperature_2m_mean",
            "precipitation_sum",
            "relative_humidity_2m_mean",
        ],
        "timezone": "UTC",
    }

    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()

    data = r.json()

    if "daily" not in data:
        return pd.DataFrame()

    df = pd.DataFrame({
        "date": pd.Series(pd.to_datetime(data["daily"]["time"])).dt.date,
        "temp": data["daily"]["temperature_2m_mean"],
        "humidity": data["daily"]["relative_humidity_2m_mean"],
        "precip": data["daily"]["precipitation_sum"],
    })

    return df


# -----------------------------------
# Build D-1 ... D-7 features
# -----------------------------------
def build_week_features(daily_df, target_date):

    out = {}
    daily_map = {d: row for d, row in daily_df.set_index("date").iterrows()}

    for k in range(1, 8):
        d = target_date - timedelta(days=k)
        row = daily_map.get(d)

        out[f"temp_d{k}"] = None if row is None else row["temp"]
        out[f"humidity_d{k}"] = None if row is None else row["humidity"]
        out[f"precip_d{k}"] = None if row is None else row["precip"]

    return out


# -----------------------------------
# MAIN
# -----------------------------------
def main():

    fires_ut = pd.read_csv("fires_utah.csv")

    fires_ut["dt"] = pd.to_datetime(
        fires_ut["attr_FireDiscoveryDateTime"],
        errors="coerce"
    )

    fires_ut = fires_ut.dropna(subset=["dt"])

    fires_ut = fires_ut.head(20)

    print("Fires Utah loaded:", len(fires_ut))

    rows = []

    for _, fire in fires_ut.iterrows():

        lat = float(fire["attr_InitialLatitude"])
        lon = float(fire["attr_InitialLongitude"])
        fire_date = fire["dt"].date()

        targets = [
            (fire_date, 1),
            (fire_date - timedelta(days=365), 0),
        ]

        for target_date, label in targets:

            start = target_date - timedelta(days=7)
            end = target_date

            daily = fetch_daily_weather(lat, lon, start, end)

            if daily.empty:
                continue

            feats = build_week_features(daily, target_date)

            row = {
                "lat": lat,
                "lon": lon,
                "target_date": str(target_date),
                "fire": label,
            }

            row.update(feats)
            rows.append(row)

            print("Processed:", target_date, "fire =", label)

    out = pd.DataFrame(rows)
    out.to_csv("training_week7_utah.csv", index=False)

    print("\nSaved rows:", len(out))


if __name__ == "__main__":
    main()