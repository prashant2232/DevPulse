import json
import asyncio
import logging
from datetime import datetime, timezone

from aiokafka import AIOKafkaConsumer
from app.config import settings
from app.redis_client import get_redis

logger = logging.getLogger(__name__)
TOPIC = "gh-events"


async def _make_consumer() -> AIOKafkaConsumer:
    for attempt in range(10):
        try:
            consumer = AIOKafkaConsumer(
                TOPIC,
                bootstrap_servers=settings.kafka_bootstrap,
                group_id="devpulse-consumers-ml",
                value_deserializer=lambda v: json.loads(v.decode("utf-8")),
                auto_offset_reset="earliest",
            )
            await consumer.start()
            return consumer
        except Exception as e:
            logger.warning(f"ML consumer Kafka not ready ({attempt+1}/10): {e}")
            await asyncio.sleep(5)
    raise RuntimeError("ML consumer: could not connect to Kafka")


async def run_ml_consumer():
    """
    For every incoming event:
    1. Accumulate today's commit total for that developer in Redis
    2. Score the total with IsolationForest
    3. If anomaly → write a Redis hash alert with 24hr TTL
    """
    # Lazy import so the app starts even if model.pkl doesn't exist yet
    try:
        from ml.model import score
        logger.info("✅ ML model loaded in consumer")
    except FileNotFoundError:
        logger.warning(
            "⚠️  model.pkl not found — ML consumer running in passthrough mode. "
            "Train the model with: docker compose exec backend python ml/train.py"
        )
        score = None

    consumer = await _make_consumer()
    r = get_redis()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    print("✅ ML consumer started")

    try:
        async for msg in consumer:
            event = msg.value
            developer = event.get("developer", "unknown")
            repo = event.get("repo", "unknown")
            commits = int(event.get("commit_count", 1))

            # ── Track daily commit total in Redis ─────────────────────────────
            daily_key = f"daily:{developer}:{today}"
            new_total = await r.incrby(daily_key, commits)
            await r.expire(daily_key, 86400 * 2)  # keep for 2 days

            # ── Score if model is available ───────────────────────────────────
            if score is None:
                continue

            result = score(developer, new_total)
            logger.info(
                f"[ml] {developer} | commits today: {new_total} | "
                f"anomaly: {result.is_anomaly} | score: {result.score}"
            )

            if result.is_anomaly:
                alert_key = f"alert:{developer}:{today}"
                await r.hset(alert_key, mapping={
                    "developer": developer,
                    "repo": repo,
                    "commits_today": new_total,
                    "score": result.score,
                    "is_anomaly": "true",
                    "detected_at": datetime.now(timezone.utc).isoformat(),
                })
                await r.expire(alert_key, 86400)  # 24hr TTL
                logger.warning(f"🚨 Anomaly detected: {developer} ({new_total} commits today)")

    finally:
        await consumer.stop()