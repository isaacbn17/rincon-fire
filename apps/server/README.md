# Server

FastAPI API + NOAA worker for Rincon Fire v1.

## Local

1. Install dependencies:

```bash
uv sync
```

2. Initialize runtime station CSV + RF artifact:

```bash
python scripts/select_stations.py --source ../../stations/stations.csv --output data/stations_runtime.csv --max-rows 200
python scripts/init_rf_model.py --output data/models/rf_baseline_untrained.joblib
```

3. Run API:

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

4. Run worker in a separate terminal:

```bash
uv run python worker.py
```

## NOAA payload verification

```bash
curl -sS -H 'accept: application/geo+json' \
  'https://api.weather.gov/stations/0007W/observations/latest?require_qc=true'
```

Required keys used by the worker transform:
- `properties.stationId`
- `properties.timestamp`
- `properties.temperature.value`
- `properties.dewpoint.value`
- `properties.relativeHumidity.value`
- `properties.windDirection.value`
- `properties.windSpeed.value`
- `properties.windGust.value`
- `properties.precipitationLast3Hours.value`
- `properties.barometricPressure.value`
