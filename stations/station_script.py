#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
import urllib.parse
import urllib.request
from typing import Any, Dict, Iterable, Optional, Tuple

from tqdm import tqdm


def _get_in(d: Dict[str, Any], path: Tuple[str, ...]) -> Any:
    cur: Any = d
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return cur


def extract_rows(payload: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    features = payload.get("features", [])
    if not isinstance(features, list):
        return

    for f in features:
        if not isinstance(f, dict):
            continue

        url = f.get("id")

        coords = _get_in(f, ("geometry", "coordinates"))
        lon: Optional[float] = None
        lat: Optional[float] = None
        if isinstance(coords, list) and len(coords) >= 2:
            lon = coords[0]
            lat = coords[1]

        elevation = _get_in(f, ("properties", "elevation", "value"))
        props = f.get("properties", {}) if isinstance(f.get("properties"), dict) else {}

        yield {
            "url": url,
            "station_identifier": props.get("stationIdentifier"),
            "latitude": lat,
            "longitude": lon,
            "elevation_m": elevation,
            "name": props.get("name"),
            "timezone": props.get("timeZone"),
            "forecast_url": props.get("forecast"),
            "fireweather_zone_url": props.get("fireWeatherZone"),
        }


def fetch_json(url: str, user_agent: str, timeout_s: int) -> Dict[str, Any]:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/geo+json",
            "User-Agent": user_agent,
        },
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        data = resp.read()
    return json.loads(data)


def iter_pages(
    *,
    per_page_limit: int,
    user_agent: str,
    timeout_s: int,
    sleep_s: float,
    max_rows: Optional[int],
) -> Iterable[Dict[str, Any]]:
    base = "https://api.weather.gov/stations"
    next_url = f"{base}?{urllib.parse.urlencode({'limit': per_page_limit})}"

    emitted = 0
    page_num = 0


    while next_url:
        page_num += 1
        payload = fetch_json(next_url, user_agent=user_agent, timeout_s=timeout_s)

        rows_on_page = 0
        for row in extract_rows(payload):
            yield row
            emitted += 1
            rows_on_page += 1
            if max_rows is not None and emitted >= max_rows:
                return


        next_url = _get_in(payload, ("pagination", "next"))
        if next_url is not None and not isinstance(next_url, str):
            next_url = None

        if next_url and sleep_s > 0:
            time.sleep(sleep_s)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Fetch NWS stations from api.weather.gov with cursor pagination and "
            "write a CSV."
        )
    )
    parser.add_argument(
        "-o",
        "--output",
        required=True,
        help="Output CSV path (use '-' for stdout).",
    )
    parser.add_argument(
        "--per-page-limit",
        type=int,
        default=500,
        help="Stations requested per page (api max is typically 500).",
    )
    parser.add_argument(
        "--max-rows",
        type=int,
        default=5000,
        help="Stop after emitting this many rows (default: 5000).",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.2,
        help="Seconds to sleep between page requests (be nice to the API).",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="HTTP timeout seconds per request.",
    )
    parser.add_argument(
        "--user-agent",
        type=str,
        default="matt-steffen-stations-csv/1.0 (contact: you@example.com)",
        help="Set a descriptive User-Agent per NWS API expectations.",
    )

    args = parser.parse_args()

    fieldnames = [
        "station_identifier",
        "name",
        "latitude",
        "longitude",
        "elevation_m",
        "timezone",
        "url",
        "forecast_url",
        "fireweather_zone_url",
    ]

    if args.output == "-":
        out_f = sys.stdout
        close_out = False
    else:
        out_f = open(args.output, "w", newline="", encoding="utf-8")
        close_out = True

    try:
        w = csv.DictWriter(out_f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()


        station_iter = iter_pages(
            per_page_limit=args.per_page_limit,
            user_agent=args.user_agent,
            timeout_s=args.timeout,
            sleep_s=args.sleep,
            max_rows=args.max_rows,
        )

        with tqdm(
            total=args.max_rows,
            desc="Stations processed",
            unit="station",
            disable=(args.output == "-"),  # Disable tqdm when writing to stdout
        ) as pbar:
            for row in station_iter:
                w.writerow(row)
                pbar.update(1)

    finally:
        if close_out:
            out_f.close()


if __name__ == "__main__":
    main()