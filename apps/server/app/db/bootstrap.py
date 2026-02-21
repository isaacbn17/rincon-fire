from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.engine import SessionLocal, engine
from app.db.models import Base, ModelPrediction, SatelliteImage, Station, WeatherObservation
from app.services.models_registry import seed_models


def init_db(reset_db: bool) -> None:
    settings = get_settings()
    settings.satellite_dir.mkdir(parents=True, exist_ok=True)

    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()
    try:
        if reset_db:
            db.query(ModelPrediction).delete()
            db.query(SatelliteImage).delete()
            db.query(WeatherObservation).delete()
            db.query(Station).delete()
            db.commit()
        seed_models(db)
    finally:
        db.close()
