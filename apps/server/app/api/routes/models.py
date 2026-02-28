from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.engine import get_db
from app.db.queries import list_models
from app.schemas.api import ModelInfo, ModelsResponse


router = APIRouter(tags=["models"])
LOGGER = logging.getLogger(__name__)


@router.get("/models", response_model=ModelsResponse)
def get_models(db: Session = Depends(get_db)) -> ModelsResponse:
    LOGGER.debug("event=api.models.request")
    models = list_models(db)
    LOGGER.debug("event=api.models.response rows_returned=%s", len(models))
    return ModelsResponse(
        models=[
            ModelInfo(model_id=row.model_id, name=row.name, description=row.description)
            for row in models
        ]
    )
