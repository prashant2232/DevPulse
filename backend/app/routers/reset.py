from fastapi import APIRouter
from sqlalchemy import text
from app.database import AsyncSessionLocal
from app.redis_client import get_redis

router = APIRouter()

@router.delete("/api/dev/reset")
async def reset_all_data():
    """Wipes all commit data, alerts and daily counters from DB and Redis."""
    
    # Clear TimescaleDB
    async with AsyncSessionLocal() as session:
        await session.execute(text("DELETE FROM commit_events"))
        await session.commit()

    # Clear Redis — alerts, daily counters, and digest
    r = get_redis()
    
    alert_keys = await r.keys("alert:*")
    daily_keys = await r.keys("daily:*")
    
    all_keys = alert_keys + daily_keys + ["weekly_digest"]
    
    if all_keys:
        await r.delete(*all_keys)

    return {
        "status": "ok",
        "cleared": {
            "alert_keys":  len(alert_keys),
            "daily_keys":  len(daily_keys),
            "digest":      True,
            "commit_rows": "all"
        }
    }