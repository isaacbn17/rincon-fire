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


def select_rows(*, source: Path, output: Path, max_rows: int) -> int:
    output.parent.mkdir(parents=True, exist_ok=True)

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

            name = _first(row, ["name"], default=station_id)
            lat = _first(row, ["lat", "latitude"])
            lon = _first(row, ["lon", "longitude"])
            if not lat or not lon:
                continue

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
            if written >= max_rows:
                break

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
    parser.add_argument("--max-rows", type=int, default=200, help="Maximum number of stations to keep.")
    args = parser.parse_args()

    count = select_rows(
        source=Path(args.source),
        output=Path(args.output),
        max_rows=max(args.max_rows, 1),
    )
    print(f"selected_stations={count}")


if __name__ == "__main__":
    main()
