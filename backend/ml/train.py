import numpy as np
import pickle
import os
from sklearn.ensemble import IsolationForest
import mlflow
import mlflow.sklearn

# ── Reproducibility ──────────────────────────────────────────────────────────
np.random.seed(42)

# ── Synthetic training data ───────────────────────────────────────────────────
# Normal developer behaviour: ~5 commits/day, std=2
normal = np.random.normal(loc=5, scale=2, size=(500, 1)).clip(min=0)

# Anomalous behaviour: bursts of >25 commits (e.g. force-push, bot activity)
anomalies = np.random.uniform(low=26, high=60, size=(20, 1))

X = np.vstack([normal, anomalies])
np.random.shuffle(X)

# ── MLflow experiment ─────────────────────────────────────────────────────────
mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "file:./mlruns"))
mlflow.set_experiment("devpulse-anomaly-detection")

with mlflow.start_run(run_name="isolation-forest-v1"):
    contamination = 0.04  # ~20 anomalies out of 520 rows ≈ 3.8%

    model = IsolationForest(
        n_estimators=100,
        contamination=contamination,
        random_state=42,
    )
    model.fit(X)

    # ── Log params & metrics to MLflow ────────────────────────────────────────
    mlflow.log_param("n_estimators", 100)
    mlflow.log_param("contamination", contamination)
    mlflow.log_param("training_samples", len(X))
    mlflow.log_param("anomaly_samples", len(anomalies))

    # Score the training set to get a rough anomaly rate
    preds = model.predict(X)
    detected = int((preds == -1).sum())
    mlflow.log_metric("anomalies_detected_train", detected)
    mlflow.log_metric("anomaly_rate_train", round(detected / len(X), 4))

    # Log the model artifact
    mlflow.sklearn.log_model(model, "isolation-forest")

    print(f"✅ Training complete — {detected}/{len(X)} anomalies flagged on training set")

# ── Save model locally for the FastAPI app to load ────────────────────────────
model_path = os.path.join(os.path.dirname(__file__), "model.pkl")
with open(model_path, "wb") as f:
    pickle.dump(model, f)

print(f"✅ Model saved to {model_path}")