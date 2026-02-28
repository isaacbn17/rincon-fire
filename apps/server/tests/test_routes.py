from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.routes.stations import router as stations_router
from app.db.engine import get_db
from app.db.models import Base, ModelPrediction, ModelRegistry, Station, WeatherObservation


def test_stations_route_returns_expected_contract() -> None:
    engine = create_engine(
        "sqlite+pysqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    with session_local() as db:  # type: Session
        db.add(ModelRegistry(model_id="rf_unbalanced", name="RF", description="rf"))
        station = Station(station_id="0007W", name="Montford Middle", lat=30.53, lon=-84.18)
        db.add(station)
        db.commit()
        db.refresh(station)

        now = datetime.now(timezone.utc)
        db.add(
            WeatherObservation(
                station_id=station.id,
                observation_id="obs-1",
                observed_at=now,
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
            )
        )
        db.add(
            ModelPrediction(
                station_id=station.id,
                model_id="rf_unbalanced",
                predicted_at=now,
                probability=0.2,
                label=0,
            )
        )
        db.commit()

    app = FastAPI()
    app.include_router(stations_router, prefix="/api/v1")

    def override_get_db():  # noqa: ANN202
        db = session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    client = TestClient(app)
    response = client.get("/api/v1/stations")

    assert response.status_code == 200
    body = response.json()
    assert "items" in body
    assert len(body["items"]) == 1
    assert body["items"][0]["area_id"] == "0007W"
    assert body["items"][0]["latest_observed_at"] is not None
    assert body["items"][0]["latest_predicted_at"] is not None
