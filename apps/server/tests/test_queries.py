from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import Base, ModelPrediction, ModelRegistry, Station
from app.db.queries import get_top_fire_areas


def test_get_top_fire_areas_sorted_and_limited() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    with session_local() as db:  # type: Session
        db.add(ModelRegistry(model_id="rf_baseline", name="RF", description="rf"))
        db.add_all(
            [
                Station(area_id="a", name="A", lat=1.0, lon=1.0),
                Station(area_id="b", name="B", lat=2.0, lon=2.0),
                Station(area_id="c", name="C", lat=3.0, lon=3.0),
            ]
        )
        db.commit()

        stations = db.query(Station).all()
        station_by_area = {s.area_id: s for s in stations}

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
        assert top_two[0][0].area_id == "b"
        assert top_two[0][1].probability == 0.9
        assert top_two[1][0].area_id == "a"
        assert top_two[1][1].probability == 0.65
