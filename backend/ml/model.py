import pickle
import numpy as np
import os
from dataclasses import dataclass

MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model.pkl")

@dataclass
class ScoreResult:
    is_anomaly: bool
    score: float
    commits_today: int

_model = None

def _load_model():
    global _model
    if _model is not None:
        return _model
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(
            f"model.pkl not found at {MODEL_PATH}. "
            "Run: python ml/train.py"
        )
    with open(MODEL_PATH, "rb") as f:
        _model = pickle.load(f)
    print(f"✅ Model loaded from {MODEL_PATH}")
    return _model

def score(developer: str, commits_today: int) -> ScoreResult:
    model = _load_model()
    X = np.array([[commits_today]])
    prediction = model.predict(X)[0]
    raw_score  = float(model.decision_function(X)[0])
    return ScoreResult(
        is_anomaly=(prediction == -1),
        score=round(raw_score, 4),
        commits_today=commits_today,
    )