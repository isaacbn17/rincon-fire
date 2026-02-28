from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.engine import SessionLocal, engine
from app.db.models import Base
from app.services.models_registry import seed_models


def _ensure_station_active_column() -> None:
    inspector = inspect(engine)
    if not inspector.has_table("stations"):
        return

    columns = {column["name"] for column in inspector.get_columns("stations")}
    if "active" in columns:
        return

    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE stations ADD COLUMN active BOOLEAN NOT NULL DEFAULT TRUE"))


def init_db(reset_db: bool) -> None:
    settings = get_settings()
    settings.satellite_dir.mkdir(parents=True, exist_ok=True)

    if reset_db:
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    _ensure_station_active_column()

    db: Session = SessionLocal()
    try:
        seed_models(db)
    finally:
        db.close()
