from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.engine import get_db
from app.db.queries import get_compare_fire_areas, get_top_fire_areas
from app.schemas.api import (
    CompareAreaItem,
    CompareAreaPrediction,
    CompareFireAreasResponse,
    FireAreaTopItem,
    FireAreasTopResponse,
    ModelInfo,
)


router = APIRouter(tags=["fire-areas"])
LOGGER = logging.getLogger(__name__)


@router.get("/fire-areas/top", response_model=FireAreasTopResponse)
def get_fire_areas_top(
    n: int = Query(default=5, ge=1, le=100),
    model_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> FireAreasTopResponse:
    settings = get_settings()
    chosen_model = model_id or settings.default_model_id
    LOGGER.debug(
        "event=api.fire_areas_top.request model_id=%s requested_n=%s",
        chosen_model,
        n,
    )
    rows = get_top_fire_areas(db, n=n, model_id=chosen_model)
    LOGGER.debug(
        "event=api.fire_areas_top.response model_id=%s requested_n=%s rows_returned=%s",
        chosen_model,
        n,
        len(rows),
    )

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


# curl -X GET "http://localhost:8000/api/v1/fire-areas/compare?n=5"
@router.get("/fire-areas/compare", response_model=CompareFireAreasResponse)
def get_fire_areas_compare(
    n: int = Query(default=5, ge=1, le=20),
    db: Session = Depends(get_db),
) -> CompareFireAreasResponse:
    models, rows = get_compare_fire_areas(db, n_per_model=n)
    model_items = [
        ModelInfo(model_id=model.model_id, name=model.name, description=model.description) for model in models
    ]
    model_ids = [model.model_id for model in models]

    sorted_rows = sorted(
        rows,
        key=lambda row: max(
            (prediction.probability for prediction in row[1].values() if prediction is not None),
            default=-1.0,
        ),
        reverse=True,
    )

    return CompareFireAreasResponse(
        models=model_items,
        items=[
            CompareAreaItem(
                area_id=station.station_id,
                name=station.name,
                lat=station.lat,
                lon=station.lon,
                predictions=[
                    CompareAreaPrediction(
                        model_id=model_id,
                        probability=predictions_by_model[model_id].probability
                        if predictions_by_model[model_id] is not None
                        else None,
                        predicted_at=predictions_by_model[model_id].predicted_at
                        if predictions_by_model[model_id] is not None
                        else None,
                    )
                    for model_id in model_ids
                ],
            )
            for station, predictions_by_model in sorted_rows
        ],
    )
