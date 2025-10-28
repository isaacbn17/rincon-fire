import pandas as pd
import numpy as np

def load_and_clean(csv_path: str) -> pd.DataFrame:
    """
    Loads the CSV with robust datetime parsing.
    Expects columns: attr_FireDiscoveryDateTime, attr_InitialLatitude, attr_InitialLongitude
    """
    # utf-8-sig handles possible BOM on header (e.g., \ufeffOBJECTID)
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    # Map columns case-insensitively
    cols = {c.lower(): c for c in df.columns}
    dt_col = next((cols[c] for c in cols if "attr_firediscoverydatetime" in c), None)
    lat_col = next((cols[c] for c in cols if "attr_initiallatitude" in c), None)
    lon_col = next((cols[c] for c in cols if "attr_initiallongitude" in c), None)
    if not all([dt_col, lat_col, lon_col]):
        raise ValueError("CSV must have 'attr_FireDiscoveryDateTime', 'attr_InitialLatitude', 'attr_InitialLongitude' columns.")

    df["ts"] = pd.to_datetime(df[dt_col], errors="coerce", infer_datetime_format=True)
    df = df.dropna(subset=["ts", lat_col, lon_col]).copy()
    df.rename(columns={lat_col: "lat", lon_col: "lon"}, inplace=True)
    return df

def bin_coord(x: float, grid: float) -> float:
    return float(np.round(x / grid) * grid)

def aggregate_regions(df: pd.DataFrame, grid: float, lookback_days: int) -> tuple[pd.DataFrame, pd.Timestamp]:
    """
    Creates lat/lon grid bins and computes:
    - count_all
    - count_recent (last lookback_days)
    - count_prior (preceding lookback_days)
    Returns (agg_df, max_ts)
    """
    df = df.copy()
    df["lat_bin"] = df["lat"].apply(lambda v: bin_coord(v, grid))
    df["lon_bin"] = df["lon"].apply(lambda v: bin_coord(v, grid))

    max_ts = df["ts"].max()
    recent_cut = max_ts - pd.Timedelta(days=lookback_days)
    prior_cut  = recent_cut - pd.Timedelta(days=lookback_days)

    grp = df.groupby(["lat_bin", "lon_bin"])
    totals = grp.size().rename("count_all")

    recent = (df[df["ts"] >= recent_cut]
              .groupby(["lat_bin", "lon_bin"])
              .size()
              .rename("count_recent"))

    prior = (df[(df["ts"] >= prior_cut) & (df["ts"] < recent_cut)]
             .groupby(["lat_bin", "lon_bin"])
             .size()
             .rename("count_prior"))

    agg = pd.concat([totals, recent, prior], axis=1).fillna(0.0).reset_index()
    agg["trend_ratio"] = (agg["count_recent"] + 1.0) / (agg["count_prior"] + 1.0)  # +1 to avoid div by zero
    # Score: emphasize recent, add baseline, reward upward trend
    agg["score"] = (0.7 * agg["count_recent"]
                    + 0.3 * np.log1p(agg["count_all"])
                    + np.log2(agg["trend_ratio"] + 1.0))
    # Keep regions with some recent activity
    agg = agg[agg["count_recent"] > 0].sort_values("score", ascending=False)
    return agg, max_ts
