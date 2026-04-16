import hashlib
import hmac
from fastapi import APIRouter, Request, HTTPException
from app.config import settings
from app.kafka.producer import produce_event

router = APIRouter()


def _verify_signature(payload: bytes, signature: str) -> bool:
    if not settings.webhook_secret or getattr(settings, "environment", "test") == "test":
        return True

    expected = "sha256=" + hmac.new(
        settings.webhook_secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


@router.post("/webhook/github")
async def github_webhook(request: Request):
    body = await request.body()
    sig = request.headers.get("X-Hub-Signature-256", "")

    if not _verify_signature(body, sig):
        raise HTTPException(status_code=401, detail="Invalid signature")

    payload = await request.json()
    event_type = request.headers.get("X-GitHub-Event", "push")

    pusher = payload.get("pusher", {}).get("name", "unknown")
    repo = payload.get("repository", {}).get("full_name", "unknown")
    commits = len(payload.get("commits", [])) or 1

    event = {
        "developer": pusher,
        "repo": repo,
        "event_type": event_type,
        "commit_count": commits,
    }

    await produce_event("gh-events", event)

    return {"status": "ok", "queued": event}