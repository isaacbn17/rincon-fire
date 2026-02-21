from __future__ import annotations

from sqlalchemy.orm import Session

from app.db import queries
from app.db.models import ModelPrediction


def get_latest_prediction(db: Session, *, area_id: str, model_id: str) -> ModelPrediction | None:
    station = queries.get_station_by_area_id(db, area_id)
    if station is None:
        return None
    return queries.get_latest_prediction_for_station(db, station_id=station.id, model_id=model_id)
