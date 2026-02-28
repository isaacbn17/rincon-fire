#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from pathlib import Path


OUTPUT_FIELDS = [
    "station_id",
    "name",
    "lat",
    "lon",
    "timezone",
    "elevation_m",
    "source_url",
]


def _first(row: dict[str, str], keys: list[str], default: str = "") -> str:
    for key in keys:
        value = row.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return default


def _load_station_id_allowlist(station_ids_file: Path) -> list[str]:
    if not station_ids_file.exists():
        raise FileNotFoundError(f"Station IDs file not found: {station_ids_file}")

    station_ids: list[str] = []
    seen: set[str] = set()
    with station_ids_file.open("r", encoding="utf-8") as fh:
        for raw_line in fh:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line in seen:
                continue
            seen.add(line)
            station_ids.append(line)

    if not station_ids:
        raise ValueError(f"Station IDs file is empty: {station_ids_file}")

    return station_ids


def select_rows(
    *,
    source: Path,
    output: Path,
    max_rows: int,
    station_ids_file: Path | None = None,
) -> int:
    output.parent.mkdir(parents=True, exist_ok=True)
    station_ids: list[str] | None = None
    allowed_ids: set[str] = set()
    seen_allowed_ids: set[str] = set()
    if station_ids_file is not None:
        station_ids = _load_station_id_allowlist(station_ids_file)
        allowed_ids = set(station_ids)

    written = 0
    with source.open("r", encoding="utf-8", newline="") as src_fh, output.open(
        "w", encoding="utf-8", newline=""
    ) as out_fh:
        reader = csv.DictReader(src_fh)
        writer = csv.DictWriter(out_fh, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()

        for row in reader:
            station_id = _first(row, ["station_id", "station_identifier", "area_id"])
            if not station_id:
                continue
            if station_ids is not None and station_id not in allowed_ids:
                continue

            name = _first(row, ["name"], default=station_id)
            lat = _first(row, ["lat", "latitude"])
            lon = _first(row, ["lon", "longitude"])
            if not lat or not lon:
                continue

            if station_ids is not None:
                seen_allowed_ids.add(station_id)

            if written < max_rows:
                writer.writerow(
                    {
                        "station_id": station_id,
                        "name": name,
                        "lat": lat,
                        "lon": lon,
                        "timezone": _first(row, ["timezone"]),
                        "elevation_m": _first(row, ["elevation_m", "elevation"]),
                        "source_url": _first(row, ["source_url", "url"]),
                    }
                )
                written += 1
                if station_ids is None and written >= max_rows:
                    break

    if station_ids is not None:
        missing = sorted(station_id for station_id in station_ids if station_id not in seen_allowed_ids)
        if missing:
            raise ValueError(f"Station IDs in {station_ids_file} were not found in {source}: {missing}")

    return written


def main() -> None:
    parser = argparse.ArgumentParser(description="Select first N stations from CSV.")
    parser.add_argument(
        "--source",
        default="/stations/stations.csv",
        help="Source stations CSV path.",
    )
    parser.add_argument(
        "--output",
        default="/app/data/stations_runtime.csv",
        help="Output stations CSV path for worker runtime.",
    )
    parser.add_argument(
        "--station-ids-file",
        default="",
        help="Optional station ID allowlist file path (one station ID per line).",
    )
    parser.add_argument("--max-rows", type=int, default=200, help="Maximum number of stations to keep.")
    args = parser.parse_args()
    station_ids_file = Path(args.station_ids_file) if args.station_ids_file.strip() else None

    count = select_rows(
        source=Path(args.source),
        output=Path(args.output),
        max_rows=max(args.max_rows, 1),
        station_ids_file=station_ids_file,
    )
    print(f"selected_stations={count}")


if __name__ == "__main__":
    main()
