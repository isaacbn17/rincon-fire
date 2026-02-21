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
from app.db.queries import insert_prediction, insert_satellite, insert_weather, list_models, upsert_station
from app.providers.predictor import MockPredictionProvider
from app.providers.satellite import MockSatelliteProvider
from app.providers.weather import MockWeatherProvider


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger("worker")


@dataclass(frozen=True)
class StationInput:
    area_id: str
    name: str
    lat: float
    lon: float


def _default_stations() -> list[StationInput]:
    return [
        StationInput(area_id="la_basin", name="Los Angeles Basin", lat=34.0522, lon=-118.2437),
        StationInput(area_id="sf_bay", name="San Francisco Bay", lat=37.7749, lon=-122.4194),
        StationInput(area_id="phoenix_metro", name="Phoenix Metro", lat=33.4484, lon=-112.0740),
        StationInput(area_id="salt_lake", name="Salt Lake City", lat=40.7608, lon=-111.8910),
        StationInput(area_id="denver_front_range", name="Denver Front Range", lat=39.7392, lon=-104.9903),
    ]


def load_stations(csv_path: Path) -> list[StationInput]:
    if not csv_path.exists():
        LOGGER.warning("Stations CSV missing at %s, using defaults", csv_path)
        return _default_stations()

    stations: list[StationInput] = []
    with csv_path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for index, row in enumerate(reader):
            try:
                area_id = (row.get("area_id") or f"area_{index + 1}").strip()
                name = (row.get("name") or area_id).strip()
                lat = float(row["lat"])
                lon = float(row["lon"])
                stations.append(StationInput(area_id=area_id, name=name, lat=lat, lon=lon))
            except Exception as exc:
                LOGGER.warning("Skipping invalid station row %s: %s", row, exc)

    if not stations:
        LOGGER.warning("No valid stations found in %s, using defaults", csv_path)
        return _default_stations()

    return stations


def run_cycle(
    *,
    db: Session,
    stations: list[StationInput],
    weather_provider: MockWeatherProvider,
    prediction_provider: MockPredictionProvider,
    satellite_provider: MockSatelliteProvider,
) -> None:
    cycle_time = datetime.now(timezone.utc)
    models = list_models(db)

    for station_input in stations:
        try:
            station = upsert_station(
                db,
                area_id=station_input.area_id,
                name=station_input.name,
                lat=station_input.lat,
                lon=station_input.lon,
            )
            weather = weather_provider.get_latest(
                area_id=station.area_id,
                lat=station.lat,
                lon=station.lon,
                observed_at=cycle_time,
            )
            insert_weather(
                db,
                station_id=station.id,
                observed_at=weather.observed_at,
                temperature_c=weather.temperature_c,
                humidity_pct=weather.humidity_pct,
                wind_speed_kph=weather.wind_speed_kph,
                precipitation_mm=weather.precipitation_mm,
            )

            for model in models:
                prediction = prediction_provider.predict(
                    model_id=model.model_id,
                    area_id=station.area_id,
                    weather=weather,
                )
                insert_prediction(
                    db,
                    station_id=station.id,
                    model_id=model.model_id,
                    predicted_at=cycle_time,
                    probability=prediction.probability,
                    label=prediction.label,
                )

            satellite = satellite_provider.get_latest(
                area_id=station.area_id,
                lat=station.lat,
                lon=station.lon,
                captured_at=cycle_time,
            )
            insert_satellite(
                db,
                station_id=station.id,
                captured_at=satellite.captured_at,
                filename=satellite.filename,
                file_path=str(satellite.file_path),
                content_type=satellite.content_type,
            )
        except Exception:
            LOGGER.exception("Failed cycle processing for station %s", station_input.area_id)


def main() -> None:
    settings = get_settings()
    init_db(reset_db=settings.reset_db_on_start)

    stations = load_stations(settings.stations_csv_path)
    weather_provider = MockWeatherProvider()
    prediction_provider = MockPredictionProvider()
    satellite_provider = MockSatelliteProvider(output_dir=settings.satellite_dir)

    LOGGER.info("Worker started with %d stations, interval=%ss", len(stations), settings.worker_interval_seconds)

    while True:
        start = time.monotonic()
        db = SessionLocal()
        try:
            run_cycle(
                db=db,
                stations=stations,
                weather_provider=weather_provider,
                prediction_provider=prediction_provider,
                satellite_provider=satellite_provider,
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
