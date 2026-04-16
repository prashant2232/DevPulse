import pickle
import numpy as np
import os
from dataclasses import dataclass

@dataclass
class ScoreResult:
    is_anomaly: bool
    score: float        # raw IsolationForest decision score (negative = more anomalous)
    commits_today: int

_model = None  # module-level singleton — loaded once

def _load_model():
    global _model
    if _model is not None:
        return _model

    model_path = os.path.join(os.path.dirname(__file__), "model.pkl")

    if not os.path.exists(model_path):
        raise FileNotFoundError(
            f"model.pkl not found at {model_path}. "
            "Run: docker compose exec backend python ml/train.py"
        )

    with open(model_path, "rb") as f:
        _model = pickle.load(f)

    print("✅ IsolationForest model loaded")
    return _model


def score(developer: str, commits_today: int) -> ScoreResult:
    """
    Score a developer's commit count for the day.
    Returns is_anomaly=True if the activity looks suspicious.
    """
    model = _load_model()
    X = np.array([[commits_today]])

    # predict returns 1 (normal) or -1 (anomaly)
    prediction = model.predict(X)[0]

    # decision_function returns a score: more negative = more anomalous
    raw_score = float(model.decision_function(X)[0])

    return ScoreResult(
        is_anomaly=(prediction == -1),
        score=round(raw_score, 4),
        commits_today=commits_today,
    )