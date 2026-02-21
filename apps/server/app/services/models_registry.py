from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ModelRegistry


DEFAULT_MODELS = [
    {
        "model_id": "rf_baseline",
        "name": "Random Forest Baseline",
        "description": "Balanced random forest baseline model.",
    },
    {
        "model_id": "xgb_imbalance",
        "name": "XGBoost Imbalance",
        "description": "Gradient boosted model tuned for class imbalance.",
    },
    {
        "model_id": "bayes_detector",
        "name": "Bayesian Detector",
        "description": "Bayesian anomaly detector for wildfire risk signals.",
    },
]


def seed_models(db: Session) -> None:
    existing = {
        row.model_id
        for row in db.execute(select(ModelRegistry.model_id)).all()
    }
    for model in DEFAULT_MODELS:
        if model["model_id"] in existing:
            continue
        db.add(ModelRegistry(**model))
    db.commit()
