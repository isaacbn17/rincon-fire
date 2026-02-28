from __future__ import annotations

import csv
from pathlib import Path

import pytest

from scripts.select_stations import select_rows


SOURCE_FIELDS = [
    "station_id",
    "name",
    "lat",
    "lon",
    "timezone",
    "elevation_m",
    "source_url",
]


def _write_source_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=SOURCE_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def _read_output_station_ids(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return [row["station_id"] for row in csv.DictReader(fh)]


def test_select_rows_filters_by_station_ids_file(tmp_path: Path) -> None:
    source = tmp_path / "source.csv"
    output = tmp_path / "output.csv"
    station_ids_file = tmp_path / "station_ids.txt"

    _write_source_csv(
        source,
        [
            {"station_id": "A", "name": "A", "lat": "1.0", "lon": "1.0"},
            {"station_id": "B", "name": "B", "lat": "2.0", "lon": "2.0"},
            {"station_id": "C", "name": "C", "lat": "3.0", "lon": "3.0"},
        ],
    )
    station_ids_file.write_text("B\nC\n", encoding="utf-8")

    written = select_rows(
        source=source,
        output=output,
        max_rows=20,
        station_ids_file=station_ids_file,
    )

    assert written == 2
    assert _read_output_station_ids(output) == ["B", "C"]


def test_select_rows_fails_for_missing_allowlisted_station_id(tmp_path: Path) -> None:
    source = tmp_path / "source.csv"
    output = tmp_path / "output.csv"
    station_ids_file = tmp_path / "station_ids.txt"

    _write_source_csv(
        source,
        [
            {"station_id": "A", "name": "A", "lat": "1.0", "lon": "1.0"},
        ],
    )
    station_ids_file.write_text("A\nMISSING\n", encoding="utf-8")

    with pytest.raises(ValueError, match="MISSING"):
        select_rows(
            source=source,
            output=output,
            max_rows=20,
            station_ids_file=station_ids_file,
        )


def test_select_rows_ignores_comments_blanks_and_duplicates_in_ids_file(tmp_path: Path) -> None:
    source = tmp_path / "source.csv"
    output = tmp_path / "output.csv"
    station_ids_file = tmp_path / "station_ids.txt"

    _write_source_csv(
        source,
        [
            {"station_id": "A", "name": "A", "lat": "1.0", "lon": "1.0"},
            {"station_id": "B", "name": "B", "lat": "2.0", "lon": "2.0"},
        ],
    )
    station_ids_file.write_text("\n# Utah stations\nB\nB\n\n", encoding="utf-8")

    written = select_rows(
        source=source,
        output=output,
        max_rows=20,
        station_ids_file=station_ids_file,
    )

    assert written == 1
    assert _read_output_station_ids(output) == ["B"]
