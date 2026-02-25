import os
import pandas as pd
import joblib

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score


class WildfireRFModel:

    # -------------------------
    # INIT
    # -------------------------
    def __init__(self):
        self.model = RandomForestClassifier(
            n_estimators=800,
            max_depth=None,
            min_samples_split=2,
            min_samples_leaf=1,
            max_features="sqrt",
            bootstrap=True,
            n_jobs=-1,
            random_state=42,
            class_weight="balanced",  # helpful if classes aren't perfectly balanced
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

        # Use .loc + .copy to avoid pandas SettingWithCopyWarning
        X_train = train_df.loc[:, self.feature_columns].copy()
        y_train = train_df["has_fire"]

        X_test = test_df.loc[:, self.feature_columns].copy()
        y_test = test_df["has_fire"]

        # RandomForest requires numeric
        X_train = X_train.apply(pd.to_numeric, errors="coerce").fillna(0)
        X_test = X_test.apply(pd.to_numeric, errors="coerce").fillna(0)

        print("Training Random Forest model...")
        self.model.fit(X_train, y_train)

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
    def predict(self, feature_row: dict):
        if self.feature_columns is None:
            raise RuntimeError("Model has not been trained/loaded (feature_columns is None).")

        df = pd.DataFrame([feature_row])

        # Add any missing columns as 0
        for col in self.feature_columns:
            if col not in df.columns:
                df[col] = 0

        df = df[self.feature_columns]
        df = df.apply(pd.to_numeric, errors="coerce").fillna(0)

        prediction = int(self.model.predict(df)[0])

        # probability of class 1
        if hasattr(self.model, "predict_proba"):
            probability = float(self.model.predict_proba(df)[0][1])
        else:
            probability = None

        return prediction, probability

    # -------------------------
    # SAVE MODEL
    # -------------------------
    def save(self, path="wildfire_rf_model.joblib", max_mb=100):
        if not path.endswith(".joblib"):
            path = path + ".joblib"

        joblib.dump(
            {
                "model": self.model,
                "features": self.feature_columns
            },
            path,
            compress=3,
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
    def load(self, path="wildfire_rf_model.joblib"):
        data = joblib.load(path)
        self.model = data["model"]
        self.feature_columns = data["features"]
        print("Model loaded.")


# -------------------------------------------------
# RUN TRAINING DIRECTLY
# -------------------------------------------------
if __name__ == "__main__":
    model = WildfireRFModel()

    # Robust paths relative to THIS file (prevents CWD issues)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    train_path = os.path.join(base_dir, "..", "train_set_balanced.csv")
    test_path = os.path.join(base_dir, "..", "test_set_balanced.csv")

    model.train(train_path=train_path, test_path=test_path)
    model.save()