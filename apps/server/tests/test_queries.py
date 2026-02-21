from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import Base, ModelPrediction, ModelRegistry, Station
from app.db.queries import get_top_fire_areas, insert_weather


def test_get_top_fire_areas_sorted_and_limited() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    with session_local() as db:  # type: Session
        db.add(ModelRegistry(model_id="rf_baseline", name="RF", description="rf"))
        db.add_all(
            [
                Station(station_id="a", name="A", lat=1.0, lon=1.0),
                Station(station_id="b", name="B", lat=2.0, lon=2.0),
                Station(station_id="c", name="C", lat=3.0, lon=3.0),
            ]
        )
        db.commit()

        stations = db.query(Station).all()
        station_by_area = {s.station_id: s for s in stations}

        now = datetime.now(timezone.utc)
        db.add_all(
            [
                ModelPrediction(
                    station_id=station_by_area["a"].id,
                    model_id="rf_baseline",
                    predicted_at=now - timedelta(seconds=10),
                    probability=0.45,
                    label=0,
                ),
                ModelPrediction(
                    station_id=station_by_area["a"].id,
                    model_id="rf_baseline",
                    predicted_at=now,
                    probability=0.65,
                    label=1,
                ),
                ModelPrediction(
                    station_id=station_by_area["b"].id,
                    model_id="rf_baseline",
                    predicted_at=now,
                    probability=0.9,
                    label=1,
                ),
                ModelPrediction(
                    station_id=station_by_area["c"].id,
                    model_id="rf_baseline",
                    predicted_at=now,
                    probability=0.2,
                    label=0,
                ),
            ]
        )
        db.commit()

        top_two = get_top_fire_areas(db, n=2, model_id="rf_baseline")

        assert len(top_two) == 2
        assert top_two[0][0].station_id == "b"
        assert top_two[0][1].probability == 0.9
        assert top_two[1][0].station_id == "a"
        assert top_two[1][1].probability == 0.65


def test_insert_weather_is_idempotent_by_observation_id() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    with session_local() as db:  # type: Session
        station = Station(station_id="abcd", name="ABCD", lat=1.0, lon=1.0)
        db.add(station)
        db.commit()
        db.refresh(station)

        observed_at = datetime.now(timezone.utc)
        row1, created1 = insert_weather(
            db,
            station_id=station.id,
            observation_id="obs-1",
            observed_at=observed_at,
            temperature_c=20.0,
            dewpoint_c=10.0,
            relative_humidity_pct=30.0,
            wind_direction_deg=180.0,
            wind_speed_kph=12.0,
            wind_gust_kph=20.0,
            precipitation_3h_mm=0.0,
            barometric_pressure_pa=101000.0,
            visibility_m=10000.0,
            heat_index_c=21.0,
        )
        row2, created2 = insert_weather(
            db,
            station_id=station.id,
            observation_id="obs-1",
            observed_at=observed_at,
            temperature_c=25.0,
            dewpoint_c=11.0,
            relative_humidity_pct=35.0,
            wind_direction_deg=200.0,
            wind_speed_kph=13.0,
            wind_gust_kph=21.0,
            precipitation_3h_mm=0.1,
            barometric_pressure_pa=101100.0,
            visibility_m=9000.0,
            heat_index_c=25.0,
        )

        assert created1 is True
        assert created2 is False
        assert row1.id == row2.id
