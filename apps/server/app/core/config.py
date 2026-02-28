from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    database_url: str
    log_level: str
    reset_db_on_start: bool
    cors_origins: list[str]
    satellite_dir: Path
    stations_csv_path: Path
    stations_source_csv_path: Path
    station_ids_file_path: Path | None
    stations_count: int
    worker_interval_seconds: float
    default_model_id: str
    noaa_base_url: str
    noaa_user_agent: str
    noaa_require_qc: bool
    noaa_timeout_seconds: float
    noaa_max_retries: int
    noaa_backoff_seconds: float
    model_artifact_dir: Path
    enabled_model_ids: list[str]
    prediction_threshold: float


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_ENABLED_MODEL_IDS = [
    "nb_balanced",
    "rf_balanced",
    "xgb_balanced",
    "nb_unbalanced",
    "rf_unbalanced",
    "xgb_unbalanced",
]


def _to_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _resolve_path(raw: str, default: Path) -> Path:
    path = Path(raw) if raw else default
    return path if path.is_absolute() else (ROOT_DIR / path).resolve()


def _normalize_log_level(value: str | None) -> str:
    level = (value or "INFO").strip().upper()
    valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
    if level not in valid_levels:
        raise ValueError(f"LOG_LEVEL must be one of {sorted(valid_levels)}; got {level}")
    return level


def _default_model_artifact_dir() -> Path:
    if ROOT_DIR.name == "server" and ROOT_DIR.parent.name == "apps":
        repo_root = ROOT_DIR.parent.parent
    else:
        repo_root = ROOT_DIR
    return repo_root / "backend" / "data" / "models"


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
        os.getenv("STATIONS_CSV_PATH", "data/stations_runtime.csv"),
        ROOT_DIR / "data" / "stations_runtime.csv",
    )
    stations_source_csv_path = _resolve_path(
        os.getenv("STATIONS_SOURCE_CSV_PATH", "/stations/stations.csv"),
        ROOT_DIR / "data" / "stations.csv",
    )
    station_ids_file_raw = (os.getenv("STATION_IDS_FILE") or "").strip()
    station_ids_file_path = (
        _resolve_path(station_ids_file_raw, ROOT_DIR / "data" / "station_ids.txt")
        if station_ids_file_raw
        else None
    )
    model_artifact_dir = _resolve_path(
        os.getenv("MODEL_ARTIFACT_DIR", str(_default_model_artifact_dir())),
        _default_model_artifact_dir(),
    )
    enabled_model_ids_raw = os.getenv("ENABLED_MODEL_IDS", ",".join(DEFAULT_ENABLED_MODEL_IDS))
    enabled_model_ids = [item.strip() for item in enabled_model_ids_raw.split(",") if item.strip()]
    if not enabled_model_ids:
        raise ValueError("ENABLED_MODEL_IDS cannot be empty")
    default_model_id = os.getenv("DEFAULT_MODEL_ID", "rf_unbalanced").strip()
    if default_model_id not in enabled_model_ids:
        raise ValueError(
            f"DEFAULT_MODEL_ID={default_model_id} must be included in ENABLED_MODEL_IDS={enabled_model_ids}"
        )

    return Settings(
        database_url=database_url,
        log_level=_normalize_log_level(os.getenv("LOG_LEVEL")),
        reset_db_on_start=_to_bool(os.getenv("RESET_DB_ON_START"), True),
        cors_origins=cors_origins,
        satellite_dir=satellite_dir,
        stations_csv_path=stations_csv_path,
        stations_source_csv_path=stations_source_csv_path,
        station_ids_file_path=station_ids_file_path,
        stations_count=max(int(os.getenv("STATIONS_COUNT", "200")), 1),
        worker_interval_seconds=float(os.getenv("WORKER_INTERVAL_SECONDS", "10")),
        default_model_id=default_model_id,
        noaa_base_url=os.getenv("NOAA_BASE_URL", "https://api.weather.gov").rstrip("/"),
        noaa_user_agent=os.getenv(
            "NOAA_USER_AGENT",
            "rincon-fire-worker/1.0 (contact: devnull@example.com)",
        ),
        noaa_require_qc=_to_bool(os.getenv("NOAA_REQUIRE_QC"), True),
        noaa_timeout_seconds=float(os.getenv("NOAA_TIMEOUT_SECONDS", "15")),
        noaa_max_retries=max(int(os.getenv("NOAA_MAX_RETRIES", "3")), 1),
        noaa_backoff_seconds=float(os.getenv("NOAA_BACKOFF_SECONDS", "1.5")),
        model_artifact_dir=model_artifact_dir,
        enabled_model_ids=enabled_model_ids,
        prediction_threshold=float(os.getenv("PREDICTION_THRESHOLD", "0.5")),
    )
