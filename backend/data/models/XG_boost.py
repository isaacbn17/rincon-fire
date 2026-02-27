import os
import sys
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import joblib

from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))
from src.api_helpers import get_formatted_weather_data


class WildfireXGBoostModel:
    """
    Simple XGBoost classifier for predicting has_fire.
    """

    # -------------------------
    # INIT
    # -------------------------
    def __init__(self):
        self.model = XGBClassifier(
            objective="binary:logistic",
            eval_metric="logloss",
            n_estimators=2000,
            learning_rate=0.03,
            max_depth=7,
            min_child_weight=1,
            subsample=0.9,
            colsample_bytree=0.9,
            reg_lambda=1.0,
            reg_alpha=0.0,
            gamma=0.0,
            tree_method="hist",
            n_jobs=max(1, os.cpu_count() or 1),
            early_stopping_rounds=50,
            random_state=42,
        )
        self.feature_columns = None

    # -------------------------
    # TRAIN
    # -------------------------
    def train(self, train_path, test_path):
        print("Loading datasets...")

        train_df = pd.read_csv(train_path)
        test_df = pd.read_csv(test_path)

        # Ensure label exists
        if "has_fire" not in train_df.columns or "has_fire" not in test_df.columns:
            raise ValueError("Missing 'has_fire' column in train/test CSV.")

        # Drop rows where label is missing
        train_df = train_df.dropna(subset=["has_fire"]).copy()
        test_df = test_df.dropna(subset=["has_fire"]).copy()

        # Force label to int (0/1)
        train_df["has_fire"] = pd.to_numeric(train_df["has_fire"], errors="coerce")
        test_df["has_fire"] = pd.to_numeric(test_df["has_fire"], errors="coerce")

        train_df = train_df.dropna(subset=["has_fire"]).copy()
        test_df = test_df.dropna(subset=["has_fire"]).copy()

        train_df["has_fire"] = train_df["has_fire"].astype(int)
        test_df["has_fire"] = test_df["has_fire"].astype(int)

        # remove non-feature columns
        drop_cols = ["id", "date_time", "has_fire"]
        self.feature_columns = [c for c in train_df.columns if c not in drop_cols]

        X_train = train_df.loc[:, self.feature_columns].copy()
        y_train = train_df["has_fire"]

        X_test  = test_df.loc[:, self.feature_columns].copy()
        y_test = test_df["has_fire"]

        # Make sure features are numeric; coerce non-numeric to NaN then fill
        X_train = X_train.apply(pd.to_numeric, errors="coerce")
        X_test  = X_test.apply(pd.to_numeric, errors="coerce")

        # Optional: fill NaNs (XGBoost can handle NaN, but this matches your NB style)
        X_train = X_train.fillna(0)
        X_test = X_test.fillna(0)

        print("Training XGBoost model...")
        self.model.fit(
            X_train,
            y_train,
            eval_set=[(X_test, y_test)],
            verbose=False,
        )

        preds = self.model.predict(X_test)
        acc = accuracy_score(y_test, preds)
        print(f"Model Accuracy: {acc:.4f}")

        # Helpful debug counts
        print("Train size:", len(train_df), "| Test size:", len(test_df))
        print("Train class counts:\n", y_train.value_counts())
        print("Test class counts:\n", y_test.value_counts())

    # -------------------------
    # PREDICT
    # -------------------------
    def predict(self):
        # Ensure model is loaded
        if self.feature_columns is None:
            raise RuntimeError("Model has not been trained/loaded (feature_columns is None).")
        
        print("Loading weather stations for prediction...\n")
        weather_stations_path = "..\weather_stations_utah_valid.csv"
        weather_stations_df = pd.read_csv(weather_stations_path)

        results = []

        print("Predicting wildfire risk for weather stations...\n")
        count = 1
        for _, row in weather_stations_df.iterrows():
            station = row["station_url"]
            latitude = row["latitude"]
            longitude = row["longitude"]

            print(f"{count}/1257 Processing station: {station}")

            try:
                formatted_weather_df = get_formatted_weather_data(station)
            except Exception as e:
                print(f"Error fetching data for station {station}: {e}\n")
                continue

            # Ensure numeric + fill
            for c in self.feature_columns:
                formatted_weather_df[c] = pd.to_numeric(formatted_weather_df[c], errors="coerce")
            formatted_weather_df = formatted_weather_df.fillna(0)

            prediction = int(self.model.predict(formatted_weather_df[self.feature_columns])[0])
            probability = float(self.model.predict_proba(formatted_weather_df[self.feature_columns])[0][1])
            print(f"Predicted has_fire: {prediction} with probability {probability:.4f}\n")

            results.append({
                "station_url": station,
                "latitude": latitude,
                "longitude": longitude,
                "fire_probability": probability
            })

            count += 1
            if count >= 10:
                break

        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        output_path = Path(f"../model_predictions/fire_predictions_{date_str}.csv")

        results_df = pd.DataFrame(results, columns=["station_url", "latitude", "longitude", "fire_probability"])
        results_df.to_csv(output_path, index=False)

        print(f"\nSaved predictions to {output_path.resolve()}")

    # -------------------------
    # SAVE MODEL
    # -------------------------
    def save(self, path="xgb_model.joblib", max_mb=100):
        if not path.endswith(".joblib"):
            path = path + ".joblib"

        joblib.dump(
            {
                "model": self.model,
                "features": self.feature_columns,
            },
            path,
            compress=3,  # 0–9, higher = smaller/slower
        )

        size_mb = os.path.getsize(path) / (1024 * 1024)
        print(f"Model saved to {path} ({size_mb:.2f} MB).")

        if size_mb > max_mb:
            raise ValueError(
                f"Saved model is too large ({size_mb:.2f} MB > {max_mb} MB). "
                "To reduce size, lower n_estimators and/or max_depth."
            )

    # -------------------------
    # LOAD MODEL
    # -------------------------
    def load(self, path="xgb_model.joblib"):
        data = joblib.load(path)
        self.model = data["model"]
        self.feature_columns = data["features"]
        print("Model loaded.")


if __name__ == "__main__":
    model = WildfireXGBoostModel()

    model.load("unbalanced_xgb_model.joblib")

    model.predict()

    # The commented code below is for training and saving the model.
    # model = WildfireXGBoostModel()

    # model.train(
    #     train_path="../train_set_unbalanced.csv",
    #     test_path="../test_set_unbalanced.csv",
    # )

    # model.save("unbalanced_xgb_model.joblib")
