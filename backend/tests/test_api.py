import json
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport


# ── Patch all external services before importing the app ─────────────────────
# This stops the app from trying to connect to real Kafka/Redis/Postgres in CI

@pytest.fixture(autouse=True)
def mock_external_services():
    redis_mock = AsyncMock()
    redis_mock.keys    = AsyncMock(return_value=[])
    redis_mock.hgetall = AsyncMock(return_value={})
    redis_mock.get     = AsyncMock(return_value=None)
    redis_mock.ping    = AsyncMock(return_value=True)

    with (
        patch("app.database.init_db",                       new_callable=AsyncMock),
        patch("app.redis_client.init_redis",                new_callable=AsyncMock),
        patch("app.redis_client.close_redis",               new_callable=AsyncMock),
        patch("app.redis_client.redis_client",              redis_mock),
        patch("app.redis_client.get_redis",                 return_value=redis_mock),
        patch("app.kafka.producer.get_producer",
              return_value=AsyncMock(send_and_wait=AsyncMock())),
        patch("app.kafka.producer.stop_producer",           new_callable=AsyncMock),
        patch("app.kafka.consumers.start_all_consumers",    new_callable=AsyncMock),
        patch("ml.ml_consumer.run_ml_consumer",             new_callable=AsyncMock),
        patch("scheduler.digest_job.generate_weekly_digest",new_callable=AsyncMock),
        patch("apscheduler.schedulers.asyncio.AsyncIOScheduler.start"),
        patch("apscheduler.schedulers.asyncio.AsyncIOScheduler.shutdown"),
    ):
        yield redis_mock


@pytest_asyncio.fixture
async def client(mock_external_services):
    """Async test client — starts the full FastAPI app in-process."""
    from app.main import app
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac


# ── Health check ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


# ── Webhook ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_webhook_valid_push(client):
    payload = {
        "pusher": {"name": "alice"},
        "repository": {"full_name": "org/repo"},
        "commits": [{}, {}, {}],
    }
    resp = await client.post(
        "/webhook/github",
        json=payload,
        headers={"X-GitHub-Event": "push"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["queued"]["developer"] == "alice"
    assert data["queued"]["commit_count"] == 3


@pytest.mark.asyncio
async def test_webhook_empty_commits(client):
    """Should default to commit_count=1 when commits list is empty."""
    payload = {
        "pusher": {"name": "bob"},
        "repository": {"full_name": "org/other"},
        "commits": [],
    }
    resp = await client.post("/webhook/github", json=payload)
    assert resp.status_code == 200
    assert resp.json()["queued"]["commit_count"] == 1


@pytest.mark.asyncio
async def test_webhook_missing_pusher(client):
    """Should use 'unknown' as developer when pusher is absent."""
    resp = await client.post(
        "/webhook/github",
        json={"repository": {"full_name": "org/repo"}, "commits": [{}]},
    )
    assert resp.status_code == 200
    assert resp.json()["queued"]["developer"] == "unknown"


# ── Metrics ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_metrics_empty(client):
    """Returns empty list when no data in DB."""
    with patch("app.routers.metrics.AsyncSessionLocal") as mock_session:
        session_mock = AsyncMock()
        session_mock.__aenter__ = AsyncMock(return_value=session_mock)
        session_mock.__aexit__ = AsyncMock(return_value=False)
        session_mock.execute = AsyncMock(
            return_value=MagicMock(fetchall=MagicMock(return_value=[]))
        )
        mock_session.return_value = session_mock

        resp = await client.get("/api/metrics")
        assert resp.status_code == 200
        assert resp.json() == {"metrics": []}


@pytest.mark.asyncio
async def test_metrics_with_data(client):
    """Returns formatted rows when DB has commit data."""
    from datetime import datetime, timezone

    fake_row = MagicMock()
    fake_row.day = datetime(2024, 6, 10, tzinfo=timezone.utc)
    fake_row.developer = "alice"
    fake_row.total_commits = 7

    with patch("app.routers.metrics.AsyncSessionLocal") as mock_session:
        session_mock = AsyncMock()
        session_mock.__aenter__ = AsyncMock(return_value=session_mock)
        session_mock.__aexit__ = AsyncMock(return_value=False)
        session_mock.execute = AsyncMock(
            return_value=MagicMock(fetchall=MagicMock(return_value=[fake_row]))
        )
        mock_session.return_value = session_mock

        resp = await client.get("/api/metrics")
        assert resp.status_code == 200
        metrics = resp.json()["metrics"]
        assert len(metrics) == 1
        assert metrics[0]["developer"] == "alice"
        assert metrics[0]["commits"] == 7


# ── Alerts ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_alerts_empty(client, mock_external_services):
    """Returns empty list when no alert keys in Redis."""
    mock_external_services.keys = AsyncMock(return_value=[])
    resp = await client.get("/api/alerts")
    assert resp.status_code == 200
    assert resp.json() == {"alerts": []}


@pytest.mark.asyncio
async def test_alerts_with_data(client, mock_external_services):
    """Returns alert data from Redis hash."""
    mock_external_services.keys = AsyncMock(return_value=["alert:mallory:2024-06-10"])
    mock_external_services.hgetall = AsyncMock(return_value={
        "developer":    "mallory",
        "repo":         "org/repo",
        "score":        "-0.142",
        "is_anomaly":   "true",
        "commits_today": "30",
        "detected_at":  "2024-06-10T03:22:00+00:00",
    })
    resp = await client.get("/api/alerts")
    assert resp.status_code == 200
    alerts = resp.json()["alerts"]
    assert len(alerts) == 1
    assert alerts[0]["developer"] == "mallory"
    assert alerts[0]["score"] == "-0.142"


# ── Digest ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_digest_no_data(client, mock_external_services):
    """Returns placeholder when no digest in Redis."""
    mock_external_services.get = AsyncMock(return_value=None)
    resp = await client.get("/api/digest")
    assert resp.status_code == 200
    data = resp.json()
    assert "summary" in data
    assert "anomaly_note" in data
    assert "recommendation" in data


@pytest.mark.asyncio
async def test_digest_with_data(client, mock_external_services):
    """Returns real digest when Redis has one."""
    digest = {
        "summary":        "Team shipped 150 commits this week.",
        "anomaly_note":   "One anomaly detected in mallory's activity.",
        "recommendation": "Add PR reviews for large batches.",
    }
    mock_external_services.get = AsyncMock(return_value=json.dumps(digest))
    resp = await client.get("/api/digest")
    assert resp.status_code == 200
    assert resp.json()["summary"] == digest["summary"]


@pytest.mark.asyncio
async def test_digest_trigger(client):
    """Manual trigger returns 200 and starts background task."""
    resp = await client.post("/api/digest/trigger")
    assert resp.status_code == 200
    assert resp.json()["status"] == "digest generation started"