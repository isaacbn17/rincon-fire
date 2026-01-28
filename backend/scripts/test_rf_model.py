"""
Quick checks for the trained random-forest model stored at data/models/rf.joblib.

Run with:
    python scripts/test_rf_model.py
"""

from __future__ import annotations

from pathlib import Path
import joblib
import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
from sklearn.model_selection import train_test_split

MODEL_PATH = Path("data/models/rf.joblib")
DATA_PATH = Path("data/fires_augmented.csv")

# Map the training column names used in the snippet to the columns in fires_augmented.csv
FEATURE_RENAME = {
    "relative_humidity": "humidity",
    "precipitation": "precipitationLast3Hours",
    "wind_direction": "windDirection",
    "wind_speed": "windSpeed",
    "wind_gust": "windGust",
    "air_pressure": "barometricPressure",
}

# Final order expected by the model (must match the training code)
FEATURE_ORDER = [
    "temperature",
    "dewpoint",
    "humidity",
    "precipitationLast3Hours",
    "windDirection",
    "windSpeed",
    "windGust",
    "barometricPressure",
]


def load_data():
    df = pd.read_csv(DATA_PATH)
    df = df.rename(columns=FEATURE_RENAME)

    missing = [col for col in FEATURE_ORDER if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns in {DATA_PATH}: {missing}")

    X = df[FEATURE_ORDER].copy()
    y = df["fire"].astype(int)

    # Basic imputation so the model does not see NaNs
    X = X.fillna(X.median(numeric_only=True))
    return train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)


def main():
    model = joblib.load(MODEL_PATH)
    X_train, X_test, y_train, y_test = load_data()

    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]

    print("Test AUC:", roc_auc_score(y_test, y_prob))
    print("\nClassification report:\n", classification_report(y_test, y_pred, digits=3))
    print("\nConfusion matrix:\n", confusion_matrix(y_test, y_pred))

    # One example prediction (first row of test set)
    sample = X_test.iloc[[0]]
    sample_prob = model.predict_proba(sample)[0, 1]
    print("\nSample features:\n", sample.to_dict(orient="records")[0])
    print("Sample wildfire probability:", sample_prob)


if __name__ == "__main__":
    main()
