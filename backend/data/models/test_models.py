import sys
from pathlib import Path
from sklearn.metrics import precision_recall_curve
import matplotlib.pyplot as plt

import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    roc_auc_score,
    precision_score,
    recall_score,
    f1_score,
    balanced_accuracy_score,
    confusion_matrix,
    classification_report,
)

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT))

# Adjust these imports to match your actual filenames
from data.models.XG_boost import WildfireXGBoostModel
from data.models.random_forest import WildfireRFModel
from data.models.naive_bayes import WildfireNBModel


BASE_DIR = Path(__file__).resolve().parent

TEST_CSV_PATH = BASE_DIR.parent / "test_set_unbalanced.csv"
TARGET_COL = "has_fire"

XGB_MODEL_PATH = BASE_DIR / "unbalanced_xgb_model.joblib"
RF_MODEL_PATH = BASE_DIR / "unbalanced_rf_model.joblib"
NB_MODEL_PATH = BASE_DIR / "unbalanced_nb_model.joblib"

THRESHOLD = 0.12


def load_test_data(csv_path: Path, target_col: str):
    df = pd.read_csv(csv_path)

    if target_col not in df.columns:
        raise ValueError(f"Missing target column '{target_col}' in {csv_path}")

    df = df.dropna(subset=[target_col]).copy()
    df[target_col] = pd.to_numeric(df[target_col], errors="coerce")
    df = df.dropna(subset=[target_col]).copy()
    df[target_col] = df[target_col].astype(int)

    return df


def evaluate_model(model_wrapper, model_name: str, df: pd.DataFrame, threshold: float = 0.5):
    model = model_wrapper.model
    feature_columns = model_wrapper.feature_columns

    if feature_columns is None:
        raise RuntimeError(f"{model_name}: feature_columns is None")

    missing_features = [c for c in feature_columns if c not in df.columns]
    if missing_features:
        raise ValueError(f"{model_name}: missing features in test set: {missing_features}")

    X_test = df.loc[:, feature_columns].copy()
    X_test = X_test.apply(pd.to_numeric, errors="coerce").fillna(0)
    y_true = df[TARGET_COL]

    if not hasattr(model, "predict_proba"):
        raise RuntimeError(f"{model_name}: underlying model does not support predict_proba")

    y_prob = model.predict_proba(X_test)[:, 1]
    y_pred = (y_prob >= threshold).astype(int)

    pr_auc = average_precision_score(y_true, y_prob)
    roc_auc = roc_auc_score(y_true, y_prob)
    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    bal_acc = balanced_accuracy_score(y_true, y_pred)
    cm = confusion_matrix(y_true, y_pred)

    print("=" * 70)
    print(f"{model_name} Evaluation")
    print("=" * 70)
    print(f"Rows: {len(df)}")
    print(f"Actual fire rate: {y_true.mean():.6f}")
    print(f"Predicted fire rate at threshold of {threshold}: {y_pred.mean():.6f}")
    print()
    print(f"PR AUC             : {pr_auc:.6f}")
    print(f"ROC AUC            : {roc_auc:.6f}")
    print(f"Precision (fire=1) : {precision:.6f}")
    print(f"Recall (fire=1)    : {recall:.6f}")
    print(f"F1 score           : {f1:.6f}")
    print(f"Balanced Accuracy  : {bal_acc:.6f}")
    print()
    print("Confusion Matrix [[TN, FP], [FN, TP]]:")
    print(cm)
    print()
    print("Classification Report:")
    print(classification_report(y_true, y_pred, digits=4, zero_division=0))
    print()

    precision, recall, thresholds = precision_recall_curve(y_true, y_prob)

    plt.plot(recall, precision)
    plt.xlabel("Recall")
    plt.ylabel("Precision")
    plt.title("Unbalanced Naive Bayes Precision-Recall Curve")
    plt.show()


if __name__ == "__main__":
    df = load_test_data(TEST_CSV_PATH, TARGET_COL)

    # xgb_model = WildfireXGBoostModel()
    # xgb_model.load(XGB_MODEL_PATH)

    # rf_model = WildfireRFModel()
    # rf_model.load(RF_MODEL_PATH)

    nb_model = WildfireNBModel()
    nb_model.load(NB_MODEL_PATH)

    # evaluate_model(xgb_model, "XGBoost", df, threshold=THRESHOLD)
    # evaluate_model(rf_model, "Random Forest", df, threshold=THRESHOLD)
    evaluate_model(nb_model, "Naive Bayes", df, threshold=THRESHOLD)