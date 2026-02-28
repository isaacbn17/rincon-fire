from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.providers.weather import WeatherObservationInput
from app.services.weather_features import build_weekly_feature_row


def _obs(*, day_offset: int, temperature: float | None = 20.0) -> WeatherObservationInput:
    base = datetime(2026, 2, 21, 18, 30, tzinfo=timezone.utc)
    observed_at = base + timedelta(days=day_offset)
    return WeatherObservationInput(
        observation_id=f"obs-{day_offset}",
        station_id="0007W",
        station_name="Montford Middle",
        observed_at=observed_at,
        temperature_c=temperature,
        dewpoint_c=10.0,
        relative_humidity_pct=70.0,
        wind_direction_deg=180.0,
        wind_speed_kph=8.0,
        wind_gust_kph=16.0,
        precipitation_3h_mm=0.1,
        barometric_pressure_pa=101500.0,
        visibility_m=None,
        heat_index_c=None,
        latitude=30.53,
        longitude=-84.18,
        elevation_m=49.1,
    )


def test_build_weekly_feature_row_outputs_expected_keys() -> None:
    observations = [_obs(day_offset=i) for i in range(-6, 1)]
    row = build_weekly_feature_row(observations, days=7, fill_value=0.0)

    assert len(row) == 56
    assert "temperature_1" in row
    assert "air_pressure_7" in row
    assert row["temperature_1"] == 20.0
    assert row["temperature_7"] == 20.0


def test_build_weekly_feature_row_pads_missing_days_and_nones() -> None:
    observations = [_obs(day_offset=-1, temperature=None), _obs(day_offset=0, temperature=33.0)]
    row = build_weekly_feature_row(observations, days=7, fill_value=0.0)

    assert row["temperature_1"] == 0.0
    assert row["temperature_6"] == 0.0
    assert row["temperature_7"] == 33.0
