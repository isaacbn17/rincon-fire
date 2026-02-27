from __future__ import annotations

import csv
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.bootstrap import init_db
from app.db.engine import SessionLocal
from app.db.queries import (
    insert_prediction,
    insert_weather,
    list_active_stations,
    set_station_active,
    upsert_station,
)
from app.providers.predictor import RandomForestFallbackPredictionProvider
from app.providers.weather import NoaaWeatherProvider, WeatherObservationInput


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger("worker")


@dataclass(frozen=True)
class StationInput:
    station_id: str
    name: str
    lat: float
    lon: float
    timezone: str | None
    elevation_m: float | None
    source_url: str | None


def _pick(row: dict[str, str], *keys: str) -> str | None:
    for key in keys:
        value = row.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _parse_float(value: str | None) -> float | None:
    if value is None or not str(value).strip():
        return None
    return float(value)


def _load_from_csv(csv_path: Path, limit: int) -> list[StationInput]:
    stations: list[StationInput] = []
    with csv_path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            station_id = _pick(row, "station_id", "station_identifier", "area_id")
            lat_raw = _pick(row, "lat", "latitude")
            lon_raw = _pick(row, "lon", "longitude")
            if not station_id or lat_raw is None or lon_raw is None:
                continue

            try:
                station = StationInput(
                    station_id=station_id,
                    name=_pick(row, "name") or station_id,
                    lat=float(lat_raw),
                    lon=float(lon_raw),
                    timezone=_pick(row, "timezone"),
                    elevation_m=_parse_float(_pick(row, "elevation_m", "elevation")),
                    source_url=_pick(row, "source_url", "url"),
                )
                stations.append(station)
            except ValueError:
                LOGGER.warning("Skipping invalid station row for station_id=%s", station_id)

            if len(stations) >= limit:
                break
    return stations


def load_stations(*, runtime_csv_path: Path, source_csv_path: Path, stations_count: int) -> list[StationInput]:
    if runtime_csv_path.exists():
        stations = _load_from_csv(runtime_csv_path, stations_count)
        if stations:
            return stations

    if source_csv_path.exists():
        stations = _load_from_csv(source_csv_path, stations_count)
        if stations:
            return stations

    raise FileNotFoundError(
        f"No valid stations found. Checked runtime={runtime_csv_path} source={source_csv_path}"
    )


def run_cycle(
    *,
    db: Session,
    weather_provider: NoaaWeatherProvider,
    predictor: RandomForestFallbackPredictionProvider,
    default_model_id: str,
) -> None:
    active_stations = list_active_stations(db)
    for station in active_stations:
        try:
            weather = weather_provider.get_latest(station_id=station.station_id)
            if isinstance(weather, int):
                LOGGER.info("Skipping station_id=%s: status=%s", station.station_id, weather)
                if weather == 404 or 500 <= weather < 600:
                    set_station_active(db, station_id=station.id, active=False)
                    LOGGER.info("Set station inactive station_id=%s due_to_status=%s", station.station_id, weather)
                continue

            if weather is None:
                LOGGER.info("Skipping station_id=%s: transient_or_parse_failure", station.station_id)
                continue

            _, created = insert_weather(
                db,
                station_id=station.id,
                observation_id=weather.observation_id,
                observed_at=weather.observed_at,
                temperature_c=weather.temperature_c,
                dewpoint_c=weather.dewpoint_c,
                relative_humidity_pct=weather.relative_humidity_pct,
                wind_direction_deg=weather.wind_direction_deg,
                wind_speed_kph=weather.wind_speed_kph,
                wind_gust_kph=weather.wind_gust_kph,
                precipitation_3h_mm=weather.precipitation_3h_mm,
                barometric_pressure_pa=weather.barometric_pressure_pa,
                visibility_m=weather.visibility_m,
                heat_index_c=weather.heat_index_c,
            )
            if not created:
                LOGGER.info(
                    "Skipping duplicate observation for station_id=%s observation_id=%s",
                    station.station_id,
                    weather.observation_id,
                )

            prediction = predictor.predict(
                model_id=default_model_id,
                area_id=station.station_id,
                weather=WeatherObservationInput(
                    observation_id=weather.observation_id,
                    station_id=weather.station_id,
                    station_name=weather.station_name,
                    observed_at=weather.observed_at,
                    temperature_c=weather.temperature_c,
                    dewpoint_c=weather.dewpoint_c,
                    relative_humidity_pct=weather.relative_humidity_pct,
                    wind_direction_deg=weather.wind_direction_deg,
                    wind_speed_kph=weather.wind_speed_kph,
                    wind_gust_kph=weather.wind_gust_kph,
                    precipitation_3h_mm=weather.precipitation_3h_mm,
                    barometric_pressure_pa=weather.barometric_pressure_pa,
                    visibility_m=weather.visibility_m,
                    heat_index_c=weather.heat_index_c,
                    latitude=station.lat,
                    longitude=station.lon,
                    elevation_m=station.elevation_m,
                ),
            )
            insert_prediction(
                db,
                station_id=station.id,
                model_id=default_model_id,
                predicted_at=datetime.now(timezone.utc),
                probability=prediction.probability,
                label=prediction.label,
            )
        except Exception:
            LOGGER.exception("Failed cycle processing for station_id=%s", station.station_id)


def sync_stations_from_csv(*, db: Session, stations: list[StationInput]) -> None:
    for station in stations:
        upsert_station(
            db,
            station_id=station.station_id,
            active=True,
            name=station.name,
            lat=station.lat,
            lon=station.lon,
            timezone=station.timezone,
            elevation_m=station.elevation_m,
            source_url=station.source_url,
        )


def main() -> None:
    settings = get_settings()
    init_db(reset_db=settings.reset_db_on_start)

    stations = load_stations(
        runtime_csv_path=settings.stations_csv_path,
        source_csv_path=settings.stations_source_csv_path,
        stations_count=settings.stations_count,
    )
    weather_provider = NoaaWeatherProvider(
        base_url=settings.noaa_base_url,
        user_agent=settings.noaa_user_agent,
        require_qc=settings.noaa_require_qc,
        timeout_seconds=settings.noaa_timeout_seconds,
        max_retries=settings.noaa_max_retries,
        backoff_seconds=settings.noaa_backoff_seconds,
    )
    predictor = RandomForestFallbackPredictionProvider(
        model_path=settings.rf_model_path,
        default_probability=settings.rf_default_probability,
        threshold=settings.rf_threshold,
    )
    db = SessionLocal()
    try:
        sync_stations_from_csv(db=db, stations=stations)
    finally:
        db.close()

    LOGGER.info(
        "Worker started with %d csv stations, interval=%ss",
        len(stations),
        settings.worker_interval_seconds,
    )

    while True:
        start = time.monotonic()
        db = SessionLocal()
        try:
            run_cycle(
                db=db,
                weather_provider=weather_provider,
                predictor=predictor,
                default_model_id=settings.default_model_id,
            )
        finally:
            db.close()

        elapsed = time.monotonic() - start
        sleep_for = settings.worker_interval_seconds - elapsed
        if sleep_for > 0:
            LOGGER.info("Cycle complete in %.2fs; sleeping %.2fs", elapsed, sleep_for)
            time.sleep(sleep_for)
        else:
            LOGGER.warning("Cycle lagging by %.2fs; starting next cycle immediately", abs(sleep_for))


if __name__ == "__main__":
    main()
