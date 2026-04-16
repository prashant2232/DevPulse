from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class WebhookPayload(BaseModel):
    """Parsed from GitHub push webhook"""
    developer: str
    repo: str
    commit_count: int
    event_type: str = "push"

class CommitMetric(BaseModel):
    time: datetime
    developer: str
    repo: str
    commit_count: int

class AlertItem(BaseModel):
    developer: str
    repo: str
    score: float
    is_anomaly: bool
    detected_at: str

class DigestReport(BaseModel):
    summary: str
    anomaly_note: str
    recommendation: str