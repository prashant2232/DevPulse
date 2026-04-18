import json
import logging
from app.config import settings

logger = logging.getLogger(__name__)
_producer = None


async def get_producer():
    global _producer
    if not settings.kafka_bootstrap:
        return None
    if _producer is None:
        from aiokafka import AIOKafkaProducer
        _producer = AIOKafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
        await _producer.start()
        logger.info("✅ Kafka producer started")
    return _producer


async def stop_producer():
    global _producer
    if _producer:
        await _producer.stop()
        _producer = None


async def produce_event(topic: str, payload: dict) -> bool:
    """Returns True if sent to Kafka, False if Kafka unavailable."""
    if not settings.kafka_bootstrap:
        return False
    try:
        producer = await get_producer()
        if producer is None:
            return False
        await producer.send_and_wait(topic, payload)
        return True
    except Exception as e:
        logger.warning(f"Kafka produce failed: {e}")
        return False