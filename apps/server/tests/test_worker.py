from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import Base, ModelPrediction, Station, WeatherObservation
from app.providers.predictor import PredictionOutput
from app.providers.weather import WeatherObservationInput
from worker import StationInput, load_stations, run_cycle, sync_stations_from_csv


class _FakeWeatherProvider:
    def __init__(
        self,
        latest_response: WeatherObservationInput | int | None,
        weekly_response: list[WeatherObservationInput] | int | None,
    ):
        self.latest_response = latest_response
        self.weekly_response = weekly_response
        self.latest_calls: list[str] = []
        self.weekly_calls: list[tuple[str, int]] = []

    def get_latest(self, *, station_id: str) -> WeatherObservationInput | int | None:
        self.latest_calls.append(station_id)
        return self.latest_response

    def get_recent_observations(self, *, station_id: str, days: int = 7) -> list[WeatherObservationInput] | int | None:
        self.weekly_calls.append((station_id, days))
        return self.weekly_response


class _FakePredictor:
    def __init__(self, model_ids: list[str], probability: float = 0.7):
        self._model_ids = model_ids
        self.probability = probability
        self.calls: list[tuple[str, str]] = []

    def available_model_ids(self) -> list[str]:
        return self._model_ids

    def predict(self, *, model_id: str, area_id: str, feature_row: dict[str, float]) -> PredictionOutput:
        self.calls.append((model_id, area_id))
        _ = feature_row
        return PredictionOutput(probability=self.probability, label=int(self.probability >= 0.5))


def _observation(*, observation_id: str = "obs-1", observed_at: datetime | None = None) -> WeatherObservationInput:
    return WeatherObservationInput(
        observation_id=observation_id,
        station_id="0007W",
        station_name="Montford Middle",
        observed_at=observed_at or datetime(2026, 2, 21, 18, 30, tzinfo=timezone.utc),
        temperature_c=26.0,
        dewpoint_c=21.0,
        relative_humidity_pct=74.0,
        wind_direction_deg=0.0,
        wind_speed_kph=0.0,
        wind_gust_kph=22.0,
        precipitation_3h_mm=None,
        barometric_pressure_pa=101500.0,
        visibility_m=None,
        heat_index_c=28.0,
        latitude=30.53,
        longitude=-84.18,
        elevation_m=49.1,
    )


def _weekly_observations(days: int = 7) -> list[WeatherObservationInput]:
    start = datetime(2026, 2, 15, 18, 30, tzinfo=timezone.utc)
    return [
        _observation(
            observation_id=f"obs-{idx + 1}",
            observed_at=start + timedelta(days=idx),
        )
        for idx in range(days)
    ]


def _station_input() -> StationInput:
    return StationInput(
        station_id="0007W",
        name="Montford Middle",
        lat=30.53,
        lon=-84.18,
        timezone="America/New_York",
        elevation_m=49.1,
        source_url="https://api.weather.gov/stations/0007W",
    )


def _write_stations_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "station_id",
                "name",
                "lat",
                "lon",
                "timezone",
                "elevation_m",
                "source_url",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def test_load_stations_filters_by_station_ids_file(tmp_path: Path) -> None:
    runtime_csv = tmp_path / "runtime.csv"
    source_csv = tmp_path / "source.csv"
    station_ids_file = tmp_path / "station_ids.txt"

    _write_stations_csv(
        runtime_csv,
        [
            {"station_id": "A", "name": "A", "lat": "1.0", "lon": "1.0"},
            {"station_id": "B", "name": "B", "lat": "2.0", "lon": "2.0"},
            {"station_id": "C", "name": "C", "lat": "3.0", "lon": "3.0"},
        ],
    )
    _write_stations_csv(source_csv, [{"station_id": "X", "name": "X", "lat": "9.0", "lon": "9.0"}])
    station_ids_file.write_text("B\nC\n", encoding="utf-8")

    stations = load_stations(
        runtime_csv_path=runtime_csv,
        source_csv_path=source_csv,
        stations_count=20,
        station_ids_file_path=station_ids_file,
    )

    assert [station.station_id for station in stations] == ["B", "C"]


def test_load_stations_station_ids_file_missing_station_fails(tmp_path: Path) -> None:
    runtime_csv = tmp_path / "runtime.csv"
    source_csv = tmp_path / "source.csv"
    station_ids_file = tmp_path / "station_ids.txt"

    _write_stations_csv(runtime_csv, [{"station_id": "A", "name": "A", "lat": "1.0", "lon": "1.0"}])
    _write_stations_csv(source_csv, [{"station_id": "A", "name": "A", "lat": "1.0", "lon": "1.0"}])
    station_ids_file.write_text("A\nMISSING\n", encoding="utf-8")

    with pytest.raises(ValueError, match="MISSING"):
        load_stations(
            runtime_csv_path=runtime_csv,
            source_csv_path=source_csv,
            stations_count=20,
            station_ids_file_path=station_ids_file,
        )


def test_load_stations_station_ids_file_ignores_comments_blanks_and_duplicates(tmp_path: Path) -> None:
    runtime_csv = tmp_path / "runtime.csv"
    source_csv = tmp_path / "source.csv"
    station_ids_file = tmp_path / "station_ids.txt"

    _write_stations_csv(
        runtime_csv,
        [
            {"station_id": "B", "name": "B", "lat": "2.0", "lon": "2.0"},
            {"station_id": "C", "name": "C", "lat": "3.0", "lon": "3.0"},
        ],
    )
    _write_stations_csv(source_csv, [{"station_id": "X", "name": "X", "lat": "9.0", "lon": "9.0"}])
    station_ids_file.write_text("\n# Utah IDs\nB\nB\n\n", encoding="utf-8")

    stations = load_stations(
        runtime_csv_path=runtime_csv,
        source_csv_path=source_csv,
        stations_count=20,
        station_ids_file_path=station_ids_file,
    )

    assert [station.station_id for station in stations] == ["B"]


def test_load_stations_station_ids_file_falls_back_to_source_for_complete_allowlist(tmp_path: Path) -> None:
    runtime_csv = tmp_path / "runtime.csv"
    source_csv = tmp_path / "source.csv"
    station_ids_file = tmp_path / "station_ids.txt"

    _write_stations_csv(runtime_csv, [{"station_id": "A", "name": "A", "lat": "1.0", "lon": "1.0"}])
    _write_stations_csv(
        source_csv,
        [
            {"station_id": "A", "name": "A", "lat": "1.0", "lon": "1.0"},
            {"station_id": "B", "name": "B", "lat": "2.0", "lon": "2.0"},
        ],
    )
    station_ids_file.write_text("A\nB\n", encoding="utf-8")

    stations = load_stations(
        runtime_csv_path=runtime_csv,
        source_csv_path=source_csv,
        stations_count=20,
        station_ids_file_path=station_ids_file,
    )

    assert [station.station_id for station in stations] == ["A", "B"]


def test_load_stations_falls_back_to_source_when_runtime_has_no_valid_rows(tmp_path: Path) -> None:
    runtime_csv = tmp_path / "runtime.csv"
    source_csv = tmp_path / "source.csv"

    _write_stations_csv(runtime_csv, [{"station_id": "BROKEN", "name": "Broken", "lat": "", "lon": ""}])
    _write_stations_csv(source_csv, [{"station_id": "GOOD", "name": "Good", "lat": "40.0", "lon": "-111.0"}])

    stations = load_stations(
        runtime_csv_path=runtime_csv,
        source_csv_path=source_csv,
        stations_count=20,
    )

    assert [station.station_id for station in stations] == ["GOOD"]


def test_sync_stations_from_csv_reactivates_existing_station() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    with session_local() as db:  # type: Session
        db.add(
            Station(
                station_id="0007W",
                active=False,
                name="Old Name",
                lat=1.0,
                lon=1.0,
            )
        )
        db.commit()

        sync_stations_from_csv(db=db, stations=[_station_input()])

        station = db.query(Station).filter(Station.station_id == "0007W").one()
        assert station.active is True
        assert station.name == "Montford Middle"


def test_run_cycle_inserts_predictions_for_all_models_and_skips_duplicate_weather() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    with session_local() as db:  # type: Session
        db.add(
            Station(
                station_id="0007W",
                active=True,
                name="Montford Middle",
                lat=30.53,
                lon=-84.18,
                timezone="America/New_York",
                elevation_m=49.1,
                source_url="https://api.weather.gov/stations/0007W",
            )
        )
        db.commit()

        weather_provider = _FakeWeatherProvider(
            latest_response=_observation(),
            weekly_response=_weekly_observations(),
        )
        predictor = _FakePredictor(model_ids=["rf_unbalanced", "xgb_unbalanced"])

        run_cycle(
            db=db,
            weather_provider=weather_provider,  # type: ignore[arg-type]
            predictor=predictor,  # type: ignore[arg-type]
        )
        run_cycle(
            db=db,
            weather_provider=weather_provider,  # type: ignore[arg-type]
            predictor=predictor,  # type: ignore[arg-type]
        )

        assert db.query(WeatherObservation).count() == 1
        assert db.query(ModelPrediction).count() == 4
        assert weather_provider.latest_calls == ["0007W", "0007W"]
        assert weather_provider.weekly_calls == [("0007W", 7), ("0007W", 7)]


def test_run_cycle_deactivates_station_for_404() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    with session_local() as db:  # type: Session
        db.add(Station(station_id="MISSING", active=True, name="Missing", lat=0.0, lon=0.0))
        db.commit()

        run_cycle(
            db=db,
            weather_provider=_FakeWeatherProvider(latest_response=404, weekly_response=None),  # type: ignore[arg-type]
            predictor=_FakePredictor(model_ids=["rf_unbalanced"]),  # type: ignore[arg-type]
        )
        run_cycle(
            db=db,
            weather_provider=_FakeWeatherProvider(latest_response=404, weekly_response=None),  # type: ignore[arg-type]
            predictor=_FakePredictor(model_ids=["rf_unbalanced"]),  # type: ignore[arg-type]
        )

        assert db.query(WeatherObservation).count() == 0
        station = db.query(Station).filter(Station.station_id == "MISSING").one()
        assert station.active is False


def test_run_cycle_none_response_keeps_station_active() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    with session_local() as db:  # type: Session
        db.add(Station(station_id="FLAKY", active=True, name="Flaky", lat=0.0, lon=0.0))
        db.commit()

        run_cycle(
            db=db,
            weather_provider=_FakeWeatherProvider(latest_response=None, weekly_response=None),  # type: ignore[arg-type]
            predictor=_FakePredictor(model_ids=["rf_unbalanced"]),  # type: ignore[arg-type]
        )

        station = db.query(Station).filter(Station.station_id == "FLAKY").one()
        assert station.active is True
        assert db.query(WeatherObservation).count() == 0
        assert db.query(ModelPrediction).count() == 0


def test_run_cycle_uses_degraded_predictions_when_weekly_fetch_fails() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    with session_local() as db:  # type: Session
        db.add(
            Station(
                station_id="0007W",
                active=True,
                name="Montford Middle",
                lat=30.53,
                lon=-84.18,
                timezone="America/New_York",
                elevation_m=49.1,
                source_url="https://api.weather.gov/stations/0007W",
            )
        )
        db.commit()

        run_cycle(
            db=db,
            weather_provider=_FakeWeatherProvider(latest_response=_observation(), weekly_response=400),  # type: ignore[arg-type]
            predictor=_FakePredictor(model_ids=["rf_unbalanced", "xgb_unbalanced"]),  # type: ignore[arg-type]
        )

        station = db.query(Station).filter(Station.station_id == "0007W").one()
        assert station.active is True
        assert db.query(WeatherObservation).count() == 1
        assert db.query(ModelPrediction).count() == 2
