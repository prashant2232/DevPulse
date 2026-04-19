import numpy as np
import pickle
import os

np.random.seed(42)
normal    = np.random.normal(loc=5, scale=2, size=(500, 1)).clip(min=0)
anomalies = np.random.uniform(low=26, high=60, size=(20, 1))
X = np.vstack([normal, anomalies])
np.random.shuffle(X)

from sklearn.ensemble import IsolationForest
model = IsolationForest(n_estimators=100, contamination=0.04, random_state=42)
model.fit(X)

preds    = model.predict(X)
detected = int((preds == -1).sum())
print(f"Training complete — {detected}/{len(X)} anomalies flagged")

try:
    import mlflow, mlflow.sklearn
    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "file:./mlruns"))
    mlflow.set_experiment("devpulse-anomaly-detection")
    with mlflow.start_run(run_name="isolation-forest-v1"):
        mlflow.log_param("n_estimators", 100)
        mlflow.log_param("contamination", 0.04)
        mlflow.log_metric("anomalies_detected_train", detected)
        mlflow.sklearn.log_model(model, "isolation-forest")
    print("MLflow logged")
except Exception as e:
    print(f"MLflow skipped: {e}")

# Use absolute path so it works from any working directory
MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model.pkl")
with open(MODEL_PATH, "wb") as f:
    pickle.dump(model, f)

print(f"✅ Model saved to {MODEL_PATH}")