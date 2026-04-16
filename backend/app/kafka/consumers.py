import json
import asyncio
from aiokafka import AIOKafkaConsumer
from sqlalchemy import text
from app.config import settings
from app.database import AsyncSessionLocal
import logging

logger = logging.getLogger(__name__)
TOPIC = "gh-events"
GROUP = "devpulse-consumers"


async def _make_consumer(group_suffix: str) -> AIOKafkaConsumer:
    """Retry connecting to Kafka — it takes ~10s to boot in Docker."""
    for attempt in range(10):
        try:
            consumer = AIOKafkaConsumer(
                TOPIC,
                bootstrap_servers=settings.kafka_bootstrap,
                group_id=f"{GROUP}-{group_suffix}",
                value_deserializer=lambda v: json.loads(v.decode("utf-8")),
                auto_offset_reset="earliest",
            )
            await consumer.start()
            return consumer
        except Exception as e:
            logger.warning(f"Kafka not ready ({attempt+1}/10): {e}")
            await asyncio.sleep(5)
    raise RuntimeError("Could not connect to Kafka after 10 attempts")


async def db_consumer():
    """Writes every event to TimescaleDB."""
    consumer = await _make_consumer("db")
    print("✅ DB consumer started")
    try:
        async for msg in consumer:
            event = msg.value
            async with AsyncSessionLocal() as session:
                await session.execute(
                    text(
                        "INSERT INTO commit_events (time, developer, repo, event_type, commit_count) "
                        "VALUES (NOW(), :developer, :repo, :event_type, :commit_count)"
                    ),
                    {
                        "developer": event.get("developer", "unknown"),
                        "repo": event.get("repo", "unknown"),
                        "event_type": event.get("event_type", "push"),
                        "commit_count": event.get("commit_count", 1),
                    },
                )
                await session.commit()
    finally:
        await consumer.stop()


async def ml_consumer():
    """Scores events for anomalies — model loaded on Day 2."""
    consumer = await _make_consumer("ml")
    print("✅ ML consumer started (stub)")
    try:
        async for msg in consumer:
            event = msg.value
            logger.info(f"[ml_consumer] received: {event}")
            # Day 2: call model.score() and write Redis alert
    finally:
        await consumer.stop()


async def log_consumer():
    """Simple audit log consumer."""
    consumer = await _make_consumer("log")
    print("✅ Log consumer started")
    try:
        async for msg in consumer:
            logger.info(f"[audit] {msg.value}")
    finally:
        await consumer.stop()


async def start_all_consumers():
    asyncio.create_task(db_consumer())
    asyncio.create_task(log_consumer())
    # ML consumer is started separately in main.py via run_ml_consumer()