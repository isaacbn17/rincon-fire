from __future__ import annotations

from app.core.config import ROOT_DIR, get_settings


def test_get_settings_station_ids_file_path_none_when_unset(monkeypatch) -> None:
    monkeypatch.delenv("STATION_IDS_FILE", raising=False)
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.station_ids_file_path is None
    get_settings.cache_clear()


def test_get_settings_station_ids_file_path_resolves_relative_path(monkeypatch) -> None:
    monkeypatch.setenv("STATION_IDS_FILE", "data/utah_station_ids.txt")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.station_ids_file_path == (ROOT_DIR / "data" / "utah_station_ids.txt").resolve()
    get_settings.cache_clear()
