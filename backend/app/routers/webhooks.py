import hashlib
import hmac
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Request, HTTPException
from sqlalchemy import text
from app.config import settings
from app.database import AsyncSessionLocal
from app.kafka.producer import produce_event

logger = logging.getLogger(__name__)
router = APIRouter()


def _verify_signature(payload: bytes, signature: str) -> bool:
    if not settings.webhook_secret:
        return True
    expected = "sha256=" + hmac.new(
        settings.webhook_secret.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


async def _write_to_db(event: dict):
    async with AsyncSessionLocal() as session:
        await session.execute(
            text(
                "INSERT INTO commit_events "
                "(time, developer, repo, event_type, commit_count) "
                "VALUES (NOW(), :developer, :repo, :event_type, :commit_count)"
            ),
            event,
        )
        await session.commit()


async def _score_and_alert(event: dict):
    """
    Run ML scoring inline when Kafka/ML consumer is not available.
    Writes a Redis alert if anomaly detected.
    """
    try:
        from ml.model import score
        from app.redis_client import get_redis

        developer = event["developer"]
        commits   = event["commit_count"]
        repo      = event["repo"]
        today     = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        r = get_redis()

        # Accumulate today's total for this developer
        daily_key = f"daily:{developer}:{today}"
        new_total = await r.incrby(daily_key, commits)
        await r.expire(daily_key, 86400 * 2)

        result = score(developer, new_total)
        logger.info(f"[ml] {developer} | total today: {new_total} | anomaly: {result.is_anomaly} | score: {result.score}")

        if result.is_anomaly:
            alert_key = f"alert:{developer}:{today}"
            await r.hset(alert_key, mapping={
                "developer":     developer,
                "repo":          repo,
                "commits_today": new_total,
                "score":         result.score,
                "is_anomaly":    "true",
                "detected_at":   datetime.now(timezone.utc).isoformat(),
            })
            await r.expire(alert_key, 86400)
            logger.warning(f"Anomaly detected: {developer} ({new_total} commits today)")

    except FileNotFoundError:
        logger.warning("model.pkl not found — skipping ML scoring")
    except Exception as e:
        logger.error(f"ML scoring failed: {e}")


@router.post("/webhook/github")
async def github_webhook(request: Request):
    body = await request.body()
    sig  = request.headers.get("X-Hub-Signature-256", "")

    if not _verify_signature(body, sig):
        raise HTTPException(status_code=401, detail="Invalid signature")

    payload    = await request.json()
    event_type = request.headers.get("X-GitHub-Event", "push")
    pusher     = payload.get("pusher", {}).get("name", "unknown")
    repo       = payload.get("repository", {}).get("full_name", "unknown")
    commits    = len(payload.get("commits", [])) or 1

    event = {
        "developer":    pusher,
        "repo":         repo,
        "event_type":   event_type,
        "commit_count": commits,
    }

    sent_to_kafka = await produce_event("gh-events", event)

    if not sent_to_kafka:
        try:
            await _write_to_db(event)
        except Exception as e:
            logger.error(f"DB write failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

        # Score inline since ML consumer is not running
        await _score_and_alert(event)

    return {"status": "ok", "queued": event}