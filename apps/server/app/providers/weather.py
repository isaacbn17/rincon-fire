from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class WeatherObservationInput:
    observed_at: datetime
    temperature_c: float
    humidity_pct: float
    wind_speed_kph: float
    precipitation_mm: float


class WeatherProvider:
    def get_latest(self, *, area_id: str, lat: float, lon: float, observed_at: datetime) -> WeatherObservationInput:
        raise NotImplementedError


class MockWeatherProvider(WeatherProvider):
    def __init__(self, *, seed_prefix: str = "rincon-fire"):
        self.seed_prefix = seed_prefix

    def get_latest(self, *, area_id: str, lat: float, lon: float, observed_at: datetime) -> WeatherObservationInput:
        ts_key = observed_at.astimezone(timezone.utc).strftime("%Y%m%d%H%M%S")
        digest = hashlib.sha256(f"{self.seed_prefix}:{area_id}:{lat}:{lon}:{ts_key}".encode("utf-8")).hexdigest()
        rng = random.Random(int(digest[:16], 16))

        return WeatherObservationInput(
            observed_at=observed_at,
            temperature_c=round(16 + rng.random() * 28, 2),
            humidity_pct=round(8 + rng.random() * 72, 2),
            wind_speed_kph=round(1 + rng.random() * 60, 2),
            precipitation_mm=round(rng.random() * 8, 2),
        )
