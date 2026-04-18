import asyncio
import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.redis_client import init_redis, close_redis
from app.kafka.producer import stop_producer
from app.kafka.consumers import start_all_consumers
from app.routers import webhooks, metrics, alerts, digest
from ml.ml_consumer import run_ml_consumer
from scheduler.digest_job import generate_weekly_digest, trigger_digest_now
from app.config import settings

logging.basicConfig(level=logging.INFO)
scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await init_redis()

    # Only start Kafka consumers if broker is configured
    if settings.kafka_bootstrap and settings.kafka_bootstrap != "kafka:9092":
        await start_all_consumers()
        asyncio.create_task(run_ml_consumer())
    else:
        print("⚠️  Kafka not configured — skipping consumers (production mode)")

    scheduler.add_job(
        generate_weekly_digest,
        CronTrigger(day_of_week="mon", hour=9, minute=0),
        id="weekly_digest",
        replace_existing=True,
    )
    scheduler.start()

    yield

    scheduler.shutdown(wait=False)
    await stop_producer()
    await close_redis()


app = FastAPI(title="DevPulse API", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://dev-pulse-two.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhooks.router)
app.include_router(metrics.router)
app.include_router(alerts.router)
app.include_router(digest.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.post("/api/digest/trigger")
async def trigger_digest():
    """Dev endpoint — manually trigger the Gemini digest without waiting for Monday."""
    asyncio.create_task(trigger_digest_now())
    return {"status": "digest generation started"}