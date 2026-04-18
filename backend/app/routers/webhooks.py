import hashlib
import hmac
import logging
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


@router.post("/webhook/github")
async def github_webhook(request: Request):
    body = await request.body()
    sig = request.headers.get("X-Hub-Signature-256", "")

    if not _verify_signature(body, sig):
        raise HTTPException(status_code=401, detail="Invalid signature")

    payload = await request.json()
    event_type = request.headers.get("X-GitHub-Event", "push")
    pusher  = payload.get("pusher", {}).get("name", "unknown")
    repo    = payload.get("repository", {}).get("full_name", "unknown")
    commits = len(payload.get("commits", [])) or 1

    event = {
        "developer":    pusher,
        "repo":         repo,
        "event_type":   event_type,
        "commit_count": commits,
    }

    # Try Kafka — always fall back to direct DB write
    sent_to_kafka = await produce_event("gh-events", event)

    if not sent_to_kafka:
        try:
            await _write_to_db(event)
            logger.info(f"Event written to DB directly: {event}")
        except Exception as e:
            logger.error(f"DB write failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    return {"status": "ok", "queued": event}