#!/usr/bin/env bash
set -euo pipefail

station_id="${1:-0007W}"
url="https://api.weather.gov/stations/${station_id}/observations/latest?require_qc=true"

echo "Requesting: ${url}"
response="$(curl -sS -H 'accept: application/geo+json' "${url}")"
echo "${response}" | jq '.properties.stationId, .properties.timestamp, .properties.temperature, .properties.windSpeed, .properties.precipitationLast3Hours'
