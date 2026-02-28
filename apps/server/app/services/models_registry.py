from __future__ import annotations

from sqlalchemy import delete
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ModelRegistry
from app.services.model_runtime import default_model_registry_rows


DEFAULT_MODELS = default_model_registry_rows()


def seed_models(db: Session) -> None:
    allowed_ids = {model["model_id"] for model in DEFAULT_MODELS}
    db.execute(delete(ModelRegistry).where(ModelRegistry.model_id.not_in(allowed_ids)))

    existing = {
        row.model_id
        for row in db.execute(select(ModelRegistry.model_id)).all()
    }
    for model in DEFAULT_MODELS:
        if model["model_id"] in existing:
            continue
        db.add(ModelRegistry(**model))
    db.commit()
