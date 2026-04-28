import pandas as pd
import numpy as np
import time
import joblib
import psutil
import matplotlib.pyplot as plt

from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score
from sklearn.preprocessing import StandardScaler

# ==========================
# OPTIONAL XGBOOST
# ==========================
USE_XGBOOST = True
try:
    from xgboost import XGBClassifier
except ImportError:
    USE_XGBOOST = False
    print("XGBoost not installed. Skipping XGBoost.")

# ==========================
# CONFIG
# ==========================
DATASET_PATH = "final_multiclass_dataset_large.csv"

BINARY_MODEL_SAVE_PATH = "binary_ddos_model.pkl"
BINARY_SCALER_SAVE_PATH = "binary_feature_scaler.pkl"

# ==========================
# LOAD DATA
# ==========================
print("Loading dataset...")
df = pd.read_csv(DATASET_PATH)

# ==========================
# FIX LABELS
# ==========================
# Some datasets may not contain original normal class after balancing
# So safest logic:
# Minimum label = normal
normal_label = df["Label"].min()

# Binary conversion
df["BinaryLabel"] = df["Label"].apply(
    lambda x: 0 if x == normal_label else 1
)

# ==========================
# FEATURES / LABELS
# ==========================
X = df.drop(["Label", "BinaryLabel"], axis=1)
y = df["BinaryLabel"]

# Clean
X.replace([np.inf, -np.inf], 0, inplace=True)
X.fillna(0, inplace=True)

# ==========================
# SCALE
# ==========================
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# Save scaler
joblib.dump(scaler, BINARY_SCALER_SAVE_PATH)

# ==========================
# SPLIT
# ==========================
X_train, X_test, y_train, y_test = train_test_split(
    X_scaled,
    y,
    test_size=0.2,
    random_state=42,
    stratify=y
)

# ==========================
# MODELS
# ==========================
models = {
    "Decision Tree": DecisionTreeClassifier(
        max_depth=20,
        random_state=42
    ),

    "Random Forest": RandomForestClassifier(
        n_estimators=200,
        max_depth=20,
        n_jobs=-1,
        random_state=42
    )
}

if USE_XGBOOST:
    models["XGBoost"] = XGBClassifier(
        n_estimators=200,
        max_depth=8,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        objective="binary:logistic",
        eval_metric="logloss",
        tree_method="hist",
        random_state=42
    )

# ==========================
# TRAIN LOOP
# ==========================
best_model = None
best_accuracy = 0
best_model_name = ""

results = []

for model_name, model in models.items():
    print(f"\n===== Training {model_name} =====")

    cpu_before = psutil.cpu_percent(interval=None)

    # Train
    start_time = time.time()
    model.fit(X_train, y_train)
    train_time = time.time() - start_time

    cpu_after = psutil.cpu_percent(interval=None)

    # Predict
    pred_start = time.time()
    y_pred = model.predict(X_test)
    prediction_time = time.time() - pred_start

    accuracy = accuracy_score(y_test, y_pred)

    print(f"\n{model_name} Accuracy: {accuracy:.4f}")
    print(f"Training Time: {train_time:.2f} sec")
    print(f"Prediction Time: {prediction_time:.4f} sec")
    print(f"CPU Usage Change: {cpu_after - cpu_before:.2f}%")

    # ==========================
    # FIXED CLASS REPORT
    # ==========================
    unique_labels = sorted(np.unique(np.concatenate([y_test, y_pred])))

    binary_label_names = {
        0: "Normal",
        1: "Attack"
    }

    target_names = [binary_label_names[label] for label in unique_labels]

    print("\nClassification Report:")
    print(classification_report(
        y_test,
        y_pred,
        labels=unique_labels,
        target_names=target_names,
        zero_division=0
    ))

    # ==========================
    # FEATURE IMPORTANCE
    # ==========================
    if hasattr(model, "feature_importances_"):
        feature_importance = pd.DataFrame({
            "Feature": X.columns,
            "Importance": model.feature_importances_
        }).sort_values(by="Importance", ascending=False)

        print("\nTop Features:")
        print(feature_importance.head(10))

    # Save results
    results.append({
        "Model": model_name,
        "Accuracy": accuracy,
        "Train Time (s)": train_time,
        "Prediction Time (s)": prediction_time,
        "CPU Change (%)": cpu_after - cpu_before
    })

    # Best model
    if accuracy > best_accuracy:
        best_accuracy = accuracy
        best_model = model
        best_model_name = model_name

# ==========================
# SAVE BEST MODEL
# ==========================
joblib.dump(best_model, BINARY_MODEL_SAVE_PATH)

print("\n=================================")
print(f"BEST BINARY MODEL: {best_model_name}")
print(f"BEST ACCURACY: {best_accuracy:.4f}")
print(f"Saved to: {BINARY_MODEL_SAVE_PATH}")
print("=================================")

# ==========================
# SAVE RESULTS
# ==========================
results_df = pd.DataFrame(results)

print("\n===== MODEL COMPARISON =====")
print(results_df)

results_df.to_csv("binary_model_comparison_results.csv", index=False)

# ==========================
# PLOT
# ==========================
plt.figure(figsize=(10, 6))
plt.bar(results_df["Model"], results_df["Accuracy"])
plt.xlabel("Model")
plt.ylabel("Accuracy")
plt.title("Binary Model Accuracy Comparison")
plt.savefig("binary_model_accuracy_comparison.png")
plt.show()