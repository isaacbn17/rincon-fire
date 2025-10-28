import os
from pathlib import Path

def load_api_key():
    """
    Loads .env at the project root and returns the Gemini API key.
    Accepts either GOOGLE_API_KEY or GEMINI_API_KEY.
    """
    # project root = parent of /src
    root = Path(__file__).resolve().parent.parent
    env_path = root / ".env"

    # Load simple KEY=VALUE pairs from .env (no external deps)
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

    key = (os.environ.get("GOOGLE_API_KEY")
           or os.environ.get("GEMINI_API_KEY")
           or "").strip()

    if not (key and key.startswith("AIza")):
        raise RuntimeError(
            "Missing/invalid API key. Put GOOGLE_API_KEY=... in .env at the project root."
        )
    return key

# Default tunables for the pipeline
DEFAULT_GRID = 1.0         # degrees (try 0.5 for finer bins)
DEFAULT_LOOKBACK = 90      # days for the 'recent' window
DEFAULT_TOPN = 30          # number of candidate regions sent to Gemini
DEFAULT_OUT = 10           # ask Gemini to return up to this many regions (5–10 recommended)
