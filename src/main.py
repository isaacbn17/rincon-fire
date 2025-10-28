import argparse
from pathlib import Path

# --- robust imports: work with `python -m src.main` OR `python src/main.py` ---
try:
    # when run as a module from project root
    from src.config import load_api_key, DEFAULT_GRID, DEFAULT_LOOKBACK, DEFAULT_TOPN, DEFAULT_OUT
    from src.preprocess import load_and_clean, aggregate_regions
    from src.risk_summarize import to_context_json
    from src.prompt_gemini import ask_gemini
except ModuleNotFoundError:
    # fallback if run directly (or PYTHONPATH not set)
    import sys
    from pathlib import Path
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "src"))
    from config import load_api_key, DEFAULT_GRID, DEFAULT_LOOKBACK, DEFAULT_TOPN, DEFAULT_OUT
    from preprocess import load_and_clean, aggregate_regions
    from risk_summarize import to_context_json
    from prompt_gemini import ask_gemini
# ---------------------------------------------------------------------------


def ensure_outputs_dir():
    out_dir = Path(__file__).resolve().parent.parent / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir

def parse_args():
    ap = argparse.ArgumentParser(description="Rank fire-risk regions with Gemini (free tier-friendly).")
    ap.add_argument("--csv", required=True, help="Path to the fire discovery CSV (e.g., data/fires.csv)")
    ap.add_argument("--grid", type=float, default=DEFAULT_GRID, help="Grid size in degrees (e.g., 1.0 or 0.5)")
    ap.add_argument("--lookback", type=int, default=DEFAULT_LOOKBACK, help="Recent lookback window in days")
    ap.add_argument("--topn", type=int, default=DEFAULT_TOPN, help="Number of top candidates to send to Gemini")
    ap.add_argument("--out", type=int, default=DEFAULT_OUT, help="Ask Gemini for up to this many regions (5–10 recommended)")
    return ap.parse_args()

def main():
    args = parse_args()
    api_key = load_api_key()
    csv_path = Path(args.csv)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    print(f"Loading: {csv_path}")
    df = load_and_clean(str(csv_path))

    print(f"Aggregating with grid={args.grid}°, lookback={args.lookback} days...")
    agg, max_ts = aggregate_regions(df, grid=args.grid, lookback_days=args.lookback)

    if agg.empty:
        print("No recent activity found in the selected window. Try increasing --lookback.")
        return

    candidates = agg.head(args.topn)
    context_json = to_context_json(candidates, grid=args.grid, lookback_days=args.lookback, max_ts=max_ts)

    out_dir = ensure_outputs_dir()
    (out_dir / "candidates.json").write_text(context_json, encoding="utf-8")
    print(f"Wrote summary for Gemini: {out_dir / 'candidates.json'}")

    print("Querying Gemini (plain-text result)...")
    result_text = ask_gemini(api_key, context_json, grid_deg=args.grid, out_min=5, out_max=min(10, max(5, args.out)))
    print("\n=== Gemini Result ===")
    print(result_text or "(No text returned)")

    (out_dir / "top_regions.txt").write_text(result_text, encoding="utf-8")
    print(f"\nSaved: {out_dir / 'top_regions.txt'}")

if __name__ == "__main__":
    main()
