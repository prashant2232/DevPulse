import json
import asyncio
from aiokafka import AIOKafkaProducer
from app.config import settings

_producer: AIOKafkaProducer = None

async def get_producer() -> AIOKafkaProducer:
    global _producer
    if _producer is None:
        _producer = AIOKafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
        await _producer.start()
        print("✅ Kafka producer started")
    return _producer

async def stop_producer():
    global _producer
    if _producer:
        await _producer.stop()

async def produce_event(topic: str, payload: dict):
    producer = await get_producer()
    await producer.send_and_wait(topic, payload)