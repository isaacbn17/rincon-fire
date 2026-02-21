from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.engine import get_db
from app.db.queries import get_top_fire_areas
from app.schemas.api import FireAreaTopItem, FireAreasTopResponse


router = APIRouter(tags=["fire-areas"])


@router.get("/fire-areas/top", response_model=FireAreasTopResponse)
def get_fire_areas_top(
    n: int = Query(default=5, ge=1, le=100),
    model_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> FireAreasTopResponse:
    settings = get_settings()
    chosen_model = model_id or settings.default_model_id
    rows = get_top_fire_areas(db, n=n, model_id=chosen_model)

    return FireAreasTopResponse(
        items=[
            FireAreaTopItem(
                area_id=station.station_id,
                name=station.name,
                lat=station.lat,
                lon=station.lon,
                predicted_at=prediction.predicted_at,
                probability=prediction.probability,
                model_id=prediction.model_id,
            )
            for station, prediction in rows
        ]
    )
