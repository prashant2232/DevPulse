import json
from fastapi import APIRouter
import app.redis_client as redis_client
from app.models import DigestReport

router = APIRouter()


@router.get("/api/digest", response_model=DigestReport)
async def get_digest():
    r = redis_client.get_redis()

    raw = await r.get("weekly_digest")

    if raw:
        if isinstance(raw, bytes):
            raw = raw.decode()

        return DigestReport(**json.loads(raw))

    return DigestReport(
        summary="No digest generated yet. Check back Monday 9am.",
        anomaly_note="No anomalies detected this week.",
        recommendation="Keep shipping! 🚀",
    )