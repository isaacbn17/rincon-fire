import os
import pandas as pd
from sklearn.naive_bayes import GaussianNB
from sklearn.metrics import accuracy_score
import joblib


class WildfireNBModel:

    # -------------------------
    # INIT
    # -------------------------
    def __init__(self):
        self.model = GaussianNB()
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

        X_train = train_df[self.feature_columns]
        y_train = train_df["has_fire"]

        X_test = test_df[self.feature_columns]
        y_test = test_df["has_fire"]

        # Optional: handle missing values in features (Naive Bayes can't handle NaN)
        X_train = X_train.fillna(0)
        X_test = X_test.fillna(0)

        print("Training Naive Bayes model...")
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

        df = pd.DataFrame([feature_row])

        df = df[self.feature_columns]

        prediction = self.model.predict(df)[0]
        probability = self.model.predict_proba(df)[0][1]

        return prediction, probability

    # -------------------------
    # SAVE MODEL
    # -------------------------
    def save(self, path="wildfire_nb_model.joblib", max_mb=100):
        if not path.endswith(".joblib"):
            path = path + ".joblib"

        joblib.dump(
            {
                "model": self.model,
                "features": self.feature_columns
            },
            path
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
    def load(self, path="wildfire_nb_model.joblib"):
        data = joblib.load(path)
        self.model = data["model"]
        self.feature_columns = data["features"]
        print("Model loaded.")


# -------------------------------------------------
# RUN TRAINING DIRECTLY
# -------------------------------------------------
if __name__ == "__main__":

    model = WildfireNBModel()

    model.train(
        train_path="../train_set_balanced.csv",
        test_path="../test_set_balanced.csv"
    )

    model.save()