from fastapi import APIRouter
import app.redis_client as redis_client

router = APIRouter()


@router.get("/api/alerts")
async def get_alerts():
    r = redis_client.get_redis()

    keys = await r.keys("alert:*")
    alerts = []

    for key in keys:
        data = await r.hgetall(key)

        if data:
            alerts.append(dict(data))

    return {"alerts": alerts}