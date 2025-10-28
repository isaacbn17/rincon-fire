import json
import pandas as pd

def to_context_json(candidates: pd.DataFrame,
                    grid: float,
                    lookback_days: int,
                    max_ts) -> str:
    """
    Builds a compact JSON string with top candidate regions and window info.
    """
    recent_start = (max_ts - pd.Timedelta(days=lookback_days)).isoformat()
    prior_start  = (max_ts - pd.Timedelta(days=2*lookback_days)).isoformat()
    recent_end   = max_ts.isoformat()

    ctx = {
        "grid_deg": grid,
        "lookback_days": lookback_days,
        "time_window": {
            "recent_start": recent_start,
            "recent_end": recent_end,
            "prior_start": prior_start
        },
        "candidates": []
    }
    for _, row in candidates.iterrows():
        ctx["candidates"].append({
            "lat_bin": float(row["lat_bin"]),
            "lon_bin": float(row["lon_bin"]),
            "count_recent": int(row["count_recent"]),
            "count_prior": int(row["count_prior"]),
            "count_all": int(row["count_all"]),
            "trend_ratio": float(round(row["trend_ratio"], 4)),
            "score": float(round(row["score"], 4))
        })
    return json.dumps(ctx, separators=(",", ":"))
