from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import Base, Station, WeatherObservation
from app.providers.weather import WeatherObservationInput
from worker import StationInput, run_cycle, sync_stations_from_csv


class _FakeWeatherProvider:
    def __init__(self, response: WeatherObservationInput | int | None):
        self.response = response
        self.calls: list[str] = []

    def get_latest(self, *, station_id: str) -> WeatherObservationInput | int | None:
        self.calls.append(station_id)
        return self.response


def _observation() -> WeatherObservationInput:
    return WeatherObservationInput(
        observation_id="obs-1",
        station_id="0007W",
        station_name="Montford Middle",
        observed_at=datetime(2026, 2, 21, 18, 30, tzinfo=timezone.utc),
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


def test_run_cycle_inserts_rows_and_skips_duplicate_observation() -> None:
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

        weather_provider = _FakeWeatherProvider(_observation())

        run_cycle(
            db=db,
            weather_provider=weather_provider,
        )
        run_cycle(
            db=db,
            weather_provider=weather_provider,
        )

        assert db.query(WeatherObservation).count() == 1
        assert weather_provider.calls == ["0007W", "0007W"]


def test_run_cycle_deactivates_station_for_404() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    with session_local() as db:  # type: Session
        db.add(Station(station_id="MISSING", active=True, name="Missing", lat=0.0, lon=0.0))
        db.commit()

        weather_provider = _FakeWeatherProvider(404)
        run_cycle(
            db=db,
            weather_provider=weather_provider,
        )
        run_cycle(
            db=db,
            weather_provider=weather_provider,
        )

        assert db.query(WeatherObservation).count() == 0
        assert db.query(Station).count() == 1
        station = db.query(Station).filter(Station.station_id == "MISSING").one()
        assert station.active is False
        assert weather_provider.calls == ["MISSING"]


def test_run_cycle_deactivates_station_for_500() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    with session_local() as db:  # type: Session
        db.add(Station(station_id="BROKEN", active=True, name="Broken", lat=0.0, lon=0.0))
        db.commit()

        run_cycle(
            db=db,
            weather_provider=_FakeWeatherProvider(500),
        )

        station = db.query(Station).filter(Station.station_id == "BROKEN").one()
        assert station.active is False
        assert db.query(WeatherObservation).count() == 0


def test_run_cycle_none_response_keeps_station_active() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    with session_local() as db:  # type: Session
        db.add(Station(station_id="FLAKY", active=True, name="Flaky", lat=0.0, lon=0.0))
        db.commit()

        run_cycle(
            db=db,
            weather_provider=_FakeWeatherProvider(None),
        )

        station = db.query(Station).filter(Station.station_id == "FLAKY").one()
        assert station.active is True
        assert db.query(WeatherObservation).count() == 0
