import joblib
import pandas as pd
import shap
import matplotlib.pyplot as plt

# Load saved bundle
bundle = joblib.load("unbalanced_xgb_model.joblib")

# Extract actual model and feature list
model = bundle["model"]
feature_cols = bundle["features"]

# Load data
df = pd.read_csv("../train_set_unbalanced.csv")

# Build X with the exact saved feature list
X = df[feature_cols].copy()

# Optional: sample for speed
# X = X.sample(500, random_state=42)

# Tree-based SHAP explainer
explainer = shap.TreeExplainer(model)
shap_values = explainer(X)

# Summary plots
shap.summary_plot(shap_values, X, max_display=10)
plt.show()

# shap.summary_plot(shap_values, X, plot_type="bar")
shap.summary_plot(shap_values, X, plot_type="bar", max_display=10)
plt.show()