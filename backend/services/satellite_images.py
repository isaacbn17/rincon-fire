from __future__ import annotations
import math
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Optional

import requests
from PIL import Image

@dataclass(frozen=True)
class SatelliteRequest:
    lat: float
    lon: float
    zoom: int
    fmt: str


def _latlon_to_tile(lat_deg: float, lon_deg: float, z: int) -> tuple[int, int]:
    """Convert latitude/longitude to XYZ tile coordinates (Web Mercator)."""
    lat_rad = math.radians(lat_deg)
    n = 2 ** z
    x_tile = int((lon_deg + 180.0) / 360.0 * n)
    y_tile = int((1.0 - math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad)) / math.pi) / 2.0 * n)
    return x_tile, y_tile


def get_satellite_image_bytes(req: SatelliteRequest) -> bytes:
    """
    Fetch a satellite tile from highsight.dev and return the raw image bytes.
    """
    api_key = os.getenv("HIGHSIGHT_API_KEY", "oGVK5TFmsM9QdYArq8UiXZGgGsHXqTcw")
    if not api_key:
        raise RuntimeError("HIGHSIGHT_API_KEY not set")

    x, y = _latlon_to_tile(req.lat, req.lon, req.zoom)
    url = f"https://api.highsight.dev/v1/satellite/{req.zoom}/{x}/{y}?key={api_key}"

    resp = requests.get(url, timeout=20)
    if resp.status_code != 200:
        raise RuntimeError(f"Highsight request failed ({resp.status_code}): {resp.text[:200]}")

    # Validate image and normalize format
    try:
        img = Image.open(BytesIO(resp.content))
    except Exception as exc:  # pragma: no cover - defensive
        raise RuntimeError(f"Failed to parse image from highsight: {exc}") from exc

    # Re-encode in requested format to ensure consistency
    fmt = req.fmt.lower()
    buf = BytesIO()
    img.save(buf, format="JPEG" if fmt == "jpeg" else fmt.upper())
    return buf.getvalue()

def build_filename(req: SatelliteRequest) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"sat_{req.lat:.6f}_{req.lon:.6f}_z{req.zoom}_{ts}.{req.fmt.lower()}"

def save_image_bytes(image_dir: Path, filename: str, data: bytes) -> Path:
    image_dir.mkdir(parents=True, exist_ok=True)
    out_path = image_dir / filename
    out_path.write_bytes(data)
    return out_path
