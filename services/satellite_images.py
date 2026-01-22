from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone

@dataclass(frozen=True)
class SatelliteRequest:
    lat: float
    lon: float
    zoom: int
    fmt: str

def get_satellite_image_bytes(req: SatelliteRequest) -> bytes:
    """
    Replace this stub with your existing method.
    Must return raw image bytes (PNG/JPG/etc).
    """
    raise NotImplementedError("Hook up your existing satellite method here.")

def build_filename(req: SatelliteRequest) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"sat_{req.lat:.6f}_{req.lon:.6f}_z{req.zoom}_{ts}.{req.fmt.lower()}"

def save_image_bytes(image_dir: Path, filename: str, data: bytes) -> Path:
    image_dir.mkdir(parents=True, exist_ok=True)
    out_path = image_dir / filename
    out_path.write_bytes(data)
    return out_path
