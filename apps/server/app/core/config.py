from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    database_url: str
    reset_db_on_start: bool
    cors_origins: list[str]
    satellite_dir: Path
    stations_csv_path: Path
    worker_interval_seconds: float
    default_model_id: str


ROOT_DIR = Path(__file__).resolve().parents[2]


def _to_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _resolve_path(raw: str, default: Path) -> Path:
    path = Path(raw) if raw else default
    return path if path.is_absolute() else (ROOT_DIR / path).resolve()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@localhost:5432/rincon_fire",
    )

    cors_raw = os.getenv("CORS_ORIGINS", "http://localhost:5173")
    cors_origins = [item.strip() for item in cors_raw.split(",") if item.strip()]

    satellite_dir = _resolve_path(
        os.getenv("SATELLITE_DIR", "data/satellite"),
        ROOT_DIR / "data" / "satellite",
    )
    stations_csv_path = _resolve_path(
        os.getenv("STATIONS_CSV_PATH", "data/stations.csv"),
        ROOT_DIR / "data" / "stations.csv",
    )

    return Settings(
        database_url=database_url,
        reset_db_on_start=_to_bool(os.getenv("RESET_DB_ON_START"), True),
        cors_origins=cors_origins,
        satellite_dir=satellite_dir,
        stations_csv_path=stations_csv_path,
        worker_interval_seconds=float(os.getenv("WORKER_INTERVAL_SECONDS", "10")),
        default_model_id=os.getenv("DEFAULT_MODEL_ID", "rf_baseline"),
    )
