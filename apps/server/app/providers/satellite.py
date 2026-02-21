from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw


@dataclass(frozen=True)
class SatelliteOutput:
    captured_at: datetime
    filename: str
    file_path: Path
    content_type: str


class SatelliteProvider:
    def get_latest(self, *, area_id: str, lat: float, lon: float, captured_at: datetime) -> SatelliteOutput:
        raise NotImplementedError


class MockSatelliteProvider(SatelliteProvider):
    def __init__(self, *, output_dir: Path, seed_prefix: str = "rincon-fire"):
        self.output_dir = output_dir
        self.seed_prefix = seed_prefix
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def get_latest(self, *, area_id: str, lat: float, lon: float, captured_at: datetime) -> SatelliteOutput:
        timestamp = captured_at.strftime("%Y%m%dT%H%M%SZ")
        filename = f"sat_{area_id}_{timestamp}.png"
        file_path = self.output_dir / filename

        digest = hashlib.sha256(f"{self.seed_prefix}:{area_id}:{lat}:{lon}:{timestamp}".encode("utf-8")).hexdigest()
        r = int(digest[0:2], 16)
        g = int(digest[2:4], 16)
        b = int(digest[4:6], 16)

        img = Image.new("RGB", (512, 512), (r, g, b))
        draw = ImageDraw.Draw(img)
        draw.text((16, 16), f"{area_id}\n{lat:.4f}, {lon:.4f}\n{captured_at.isoformat()}", fill=(255, 255, 255))
        img.save(file_path, format="PNG")

        return SatelliteOutput(
            captured_at=captured_at,
            filename=filename,
            file_path=file_path,
            content_type="image/png",
        )
