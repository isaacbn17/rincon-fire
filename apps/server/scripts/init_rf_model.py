#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import joblib
from sklearn.ensemble import RandomForestClassifier


def init_model(*, output_path: Path, overwrite: bool) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists() and not overwrite:
        return

    model = RandomForestClassifier(
        n_estimators=100,
        random_state=42,
        n_jobs=1,
    )
    joblib.dump(model, output_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize untrained RF model artifact.")
    parser.add_argument(
        "--output",
        default="/app/data/models/rf_baseline_untrained.joblib",
        help="Output path for RF artifact.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite model file if it already exists.",
    )
    args = parser.parse_args()

    output_path = Path(args.output)
    init_model(output_path=output_path, overwrite=args.overwrite)
    print(f"rf_model_path={output_path}")


if __name__ == "__main__":
    main()
