from __future__ import annotations

from app.providers.weather import WeatherObservationInput


FEATURE_SPECS: tuple[tuple[str, str], ...] = (
    ("temperature", "temperature_c"),
    ("dewpoint", "dewpoint_c"),
    ("relative_humidity", "relative_humidity_pct"),
    ("precipitation", "precipitation_3h_mm"),
    ("wind_direction", "wind_direction_deg"),
    ("wind_speed", "wind_speed_kph"),
    ("wind_gust", "wind_gust_kph"),
    ("air_pressure", "barometric_pressure_pa"),
)


def build_weekly_feature_row(
    observations: list[WeatherObservationInput],
    *,
    days: int = 7,
    fill_value: float = 0.0,
) -> dict[str, float]:
    if days <= 0:
        return {}

    ordered = sorted(observations, key=lambda item: item.observed_at)
    trimmed = ordered[-days:]
    padding = [None] * max(days - len(trimmed), 0)
    padded = padding + trimmed

    feature_row: dict[str, float] = {}
    for index, obs in enumerate(padded, start=1):
        for feature_prefix, attr_name in FEATURE_SPECS:
            value = getattr(obs, attr_name) if obs is not None else None
            feature_row[f"{feature_prefix}_{index}"] = _to_float(value, default=fill_value)

    return feature_row


def _to_float(value: float | None, *, default: float) -> float:
    if value is None:
        return default
    return float(value)
