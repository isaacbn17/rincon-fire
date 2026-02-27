from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND_DIR))

# ----------------------------
# Imports
# ----------------------------
import os
import pandas as pd

from services.satellite_images import (
    SatelliteRequest,
    build_filename,
    get_satellite_image_bytes,
    save_image_bytes,
)

# ----------------------------
# Paths
# ----------------------------
PRED_DIR = (BACKEND_DIR / "data" / "model_predictions").resolve()

csv_files = sorted(PRED_DIR.glob("*.csv"))
if not csv_files:
    raise FileNotFoundError(f"No CSV files found in {PRED_DIR}")

PRED_CSV = csv_files[-1]


def _pick_col(df: pd.DataFrame, candidates: list[str]) -> str:
    lower_map = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand.lower() in lower_map:
            return lower_map[cand.lower()]
    raise KeyError(f"Missing required column. Tried: {candidates}. Found: {list(df.columns)}")


def main():

    if not PRED_CSV.exists():
        raise FileNotFoundError(f"Could not find predictions CSV at: {PRED_CSV}")

    df = pd.read_csv(PRED_CSV)


    lat_col = _pick_col(df, ["lat", "latitude"])
    lon_col = _pick_col(df, ["lon", "lng", "longitude"])

    conf_col = None
    for name in [
        "confidence",
        "wildfire_probability",
        "probability",
        "proba",
        "fire_probability",
        "score",
    ]:
        try:
            conf_col = _pick_col(df, [name])
            break
        except KeyError:
            continue

    if conf_col is None:
        raise KeyError(
            f"Could not find confidence column. Columns found: {list(df.columns)}"
        )

    df[lat_col] = pd.to_numeric(df[lat_col], errors="coerce")
    df[lon_col] = pd.to_numeric(df[lon_col], errors="coerce")
    df[conf_col] = pd.to_numeric(df[conf_col], errors="coerce")

    df = df.dropna(subset=[lat_col, lon_col, conf_col])

    if df.empty:
        print("No valid rows found.")
        return

    top3 = df.sort_values(conf_col, ascending=False).head(3).reset_index(drop=True)

    zoom = 8
    fmt = "png"

    print(f"Using columns: lat={lat_col}, lon={lon_col}, confidence={conf_col}")
    print("Top 3 predictions:\n", top3[[lat_col, lon_col, conf_col]])

    saved_files = []

    for i, row in top3.iterrows():
        lat = float(row[lat_col])
        lon = float(row[lon_col])
        conf = float(row[conf_col])

        req = SatelliteRequest(lat=lat, lon=lon, zoom=zoom, fmt=fmt)

        try:
            img_bytes = get_satellite_image_bytes(req)
        except Exception as exc:
            print(f"[{i}] Failed for ({lat}, {lon}): {exc}")
            continue

        filename = build_filename(req)
        out_path = save_image_bytes(PRED_DIR, filename, img_bytes)

        saved_files.append((conf, out_path.name))
        print(f"[{i}] Saved {out_path.name} (confidence={conf:.4f})")

    if saved_files:
        print("\nSaved images:")
        for conf, fname in saved_files:
            print(f" - {fname} (confidence={conf:.4f})")
    else:
        print("No images saved.")


if __name__ == "__main__":
    main()