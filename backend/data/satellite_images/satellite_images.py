from __future__ import annotations
import os
import math
import requests
import pandas as pd
from io import BytesIO
from pathlib import Path
from PIL import Image
from dataclasses import dataclass
from datetime import datetime, timezone

@dataclass(frozen=True)
class SatelliteManager:
    input_filepath: str
    output_dir: Path = Path("images")
    zoom: int = 8
    fmt: str = 'png'

    def _latlon_to_tile(self, lat_deg: float, lon_deg: float, z: int) -> tuple[int, int]:
        lat_rad = math.radians(lat_deg)
        n = 2 ** z
        x_tile = int((lon_deg + 180.0) / 360.0 * n)
        y_tile = int((1.0 - math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad)) / math.pi) / 2.0 * n)
        return x_tile, y_tile

    def get_satellite_image_bytes(self, lat: float, lon: float) -> bytes:
        api_key = os.getenv("HIGHSIGHT_API_KEY", "oGVK5TFmsM9QdYArq8UiXZGgGsHXqTcw")

        x, y = self._latlon_to_tile(lat, lon, self.zoom)
        url = f"https://api.highsight.dev/v1/satellite/{self.zoom}/{x}/{y}?key={api_key}"

        resp = requests.get(url, timeout=20)
        if resp.status_code != 200:
            raise RuntimeError(f"Highsight request failed ({resp.status_code}): {resp.text[:200]}")

        try:
            img = Image.open(BytesIO(resp.content))
        except Exception as exc:
            raise RuntimeError(f"Failed to parse image from highsight: {exc}") from exc

        buf = BytesIO()
        img.save(buf, format="JPEG" if self.fmt.lower() == "jpeg" else self.fmt.upper())
        return buf.getvalue()

    def build_filename(self, lat: float, lon: float) -> str:
        ts = datetime.now(timezone.utc).strftime("utchourminute%H-%M")
        return f"{lat:.2f}_{lon:.2f}_z{self.zoom}_{ts}.{self.fmt.lower()}"

    def save_image_bytes(self, filename: str, data: bytes) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        out_path = self.output_dir / filename
        out_path.write_bytes(data)
        return out_path

    def run(self, number_of_images: int = 1):
        df = pd.read_csv(self.input_filepath)
        top_rows = df.nlargest(number_of_images, 'fire_probability')
        
        for i, row in top_rows.iterrows():
            lat, lon = float(row['latitude']), float(row['longitude'])
            conf = float(row['fire_probability'])

            try:
                img_bytes = self.get_satellite_image_bytes(lat, lon)
                filename = self.build_filename(lat, lon)
                out_path = self.save_image_bytes(filename, img_bytes)
                print(f"[{i}] Saved {out_path.name} (confidence={conf:.4f})")
            except Exception as exc:
                print(f"[{i}] Failed for ({lat}, {lon}): {exc}")

if __name__ == "__main__":
    manager = SatelliteManager(
        input_filepath="../model_predictions/test.csv",
        # input_filepath="../model_predictions/fire_predictions_2026-02-28.csv",
        output_dir=Path("2026-03-02_satellite_images"),
    )
    manager.run(number_of_images=1)
