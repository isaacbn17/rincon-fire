# Server

FastAPI API + NOAA worker for Rincon Fire v1.

## Local

1. Install dependencies:

```bash
uv sync
```

2. Initialize runtime station CSV:

```bash
python scripts/select_stations.py --source ../../stations/stations.csv --output data/stations_runtime.csv --max-rows 200
```

If you want to force a fixed set of stations (for example, all Utah stations), provide a station ID file:

```bash
python scripts/select_stations.py \
  --source ../../stations/stations.csv \
  --output data/stations_runtime.csv \
  --max-rows 200 \
  --station-ids-file ../../stations/utah_station_ids.txt
```

`--station-ids-file` format:
- One station ID per line.
- Blank lines are ignored.
- Lines starting with `#` are ignored.
- Duplicate IDs are de-duplicated.
- If any ID in the file is not found in the source CSV, the command fails fast.

3. Ensure model artifacts exist in `../../backend/data/models` (balanced + unbalanced NB/RF/XGB joblibs).

4. Run API:

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

5. Run worker in a separate terminal:

```bash
uv run python worker.py
```

## Station ID allowlist via env

Set `STATION_IDS_FILE` to force the worker to use only listed station IDs:

```bash
export STATION_IDS_FILE=../../stations/utah_station_ids.txt
```

When `STATION_IDS_FILE` is set:
- Only those station IDs are used.
- Any allowlisted ID missing from the stations CSV causes startup to fail.

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



## Data lifecycle

- Postgres service + DB URL: apps/docker-compose.yml (/Users/mattsteffen/projects/llm/rincon-fire/apps/docker-compose.yml)
- ORM tables: models.py (/Users/mattsteffen/projects/llm/rincon-fire/apps/server/app/db/models.py)
- Insert/query behavior: queries.py (/Users/mattsteffen/projects/llm/rincon-fire/apps/server/app/db/queries.py)
- Worker write loop: worker.py (/Users/mattsteffen/projects/llm/rincon-fire/apps/server/worker.py)

### What data is stored (relevant tables)

- stations: one row per station/area (station_id, name, lat/lon, active, etc.)
- weather_observations: NOAA observation snapshots tied to stations.id
    - Has unique constraint on observation_id (dedupe key)
- model_predictions: prediction rows tied to stations.id + models.model_id
    - No uniqueness constraint, so predictions accumulate over time

### Example row shape

#### Example station:
```
stations
id=12
station_id='0007W'
active=true
name='Montford Middle'
lat=30.53
lon=-84.18
timezone='America/New_York'
elevation_m=49.1
source_url='https://api.weather.gov/stations/0007W'
```
#### Example weather row:
```
weather_observations
id=981
station_id=12
observation_id='https://api.weather.gov/stations/0007W/observations/2026-02-21T18:30:00+00:00'
observed_at='2026-02-21T18:30:00Z'
temperature_c=26.0
dewpoint_c=21.0
relative_humidity_pct=74.0
wind_direction_deg=0.0
wind_speed_kph=0.0
wind_gust_kph=22.0
precipitation_3h_mm=NULL
barometric_pressure_pa=101500.0
visibility_m=NULL
heat_index_c=28.0
```
#### Example prediction rows from same cycle/time (one per model):
```
model_predictions
id=4401 station_id=12 model_id='rf_unbalanced' predicted_at='2026-02-21T18:31:05Z' probability=0.72 label=1
id=4402 station_id=12 model_id='xgb_unbalanced' predicted_at='2026-02-21T18:31:05Z' probability=0.66 label=1
id=4403 station_id=12 model_id='nb_balanced'   predicted_at='2026-02-21T18:31:05Z' probability=0.41 label=0
```
### Data lifecycle

1. Startup:

- Server and worker both run init_db() (create tables, optionally drop if reset flag, seed models): bootstrap.py (/Users/
  mattsteffen/projects/llm/rincon-fire/apps/server/app/db/bootstrap.py)
- In compose, RESET_DB_ON_START=false, so data persists across restarts unless you change that.

2. Station sync:

- Worker loads station CSV and upsert_station(...) for each.
- Existing station rows are updated/re-activated (active=true).

3. Per worker cycle (WORKER_INTERVAL_SECONDS, default 10s):

- Reads active stations only.
- Fetches latest NOAA observation + recent 7-day observations.
- Inserts weather only if observation_id is new (idempotent dedupe).
- Builds weekly feature vector and inserts one prediction row per enabled model.

4. Error handling / station state:

- If NOAA latest or weekly call returns 404 or 5xx, station is marked inactive and skipped on future cycles.
- Transient parse/network None does not deactivate; it just skips that cycle.

5. Read path (API):

- “latest weather” = max observed_at for station.
- “latest prediction” = max predicted_at for station + model.
- Top fire areas picks latest prediction per station, then sorts by probability.
- Compare fire areas unions the top N areas for each model, then returns latest per-model probabilities for every area in that union.

6. Retention:

- No pruning/TTL for weather or predictions currently. Weather grows by unique observation; predictions grow every cycle/
  model.
