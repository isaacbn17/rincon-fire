import os
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class Config:
    MODEL_PATH: Path = Path(os.getenv("MODEL_PATH", "data/models/rf.joblib"))
    MODEL_VERSION: str = os.getenv("MODEL_VERSION", "rf_v1")

    IMAGE_DIR: Path = Path(os.getenv("IMAGE_DIR", "data/images"))
    STATIONS_DIR: Path = Path(os.getenv("STATIONS_DIR", "src/weather_stations.csv"))
    
    # Flask limits (protects you from huge payloads)
    MAX_CONTENT_LENGTH: int = int(os.getenv("MAX_CONTENT_LENGTH", str(2 * 1024 * 1024)))  # 2MB

def ensure_dirs(cfg: Config) -> None:
    cfg.IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    cfg.MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
