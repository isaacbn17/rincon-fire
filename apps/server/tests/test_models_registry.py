from __future__ import annotations

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import Base, ModelRegistry
from app.services.models_registry import seed_models


def test_seed_models_replaces_with_supported_catalog_ids() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    with session_local() as db:  # type: Session
        db.add(ModelRegistry(model_id="xgb_imbalance", name="xgb", description="xgb"))
        db.add(ModelRegistry(model_id="bayes_detector", name="bayes", description="bayes"))
        db.commit()

        seed_models(db)

        model_ids = sorted(list(db.execute(select(ModelRegistry.model_id)).scalars()))
        assert model_ids == [
            "nb_balanced",
            "nb_unbalanced",
            "rf_balanced",
            "rf_unbalanced",
            "xgb_balanced",
            "xgb_unbalanced",
        ]
