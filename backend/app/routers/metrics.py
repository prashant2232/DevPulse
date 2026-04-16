from fastapi import APIRouter
from sqlalchemy import text
from app.database import AsyncSessionLocal

router = APIRouter()

@router.get("/api/metrics")
async def get_metrics():
    """Commits per developer per day for the last 7 days."""
    sql = text("""
        SELECT
            time_bucket('1 day', time) AS day,
            developer,
            SUM(commit_count) AS total_commits
        FROM commit_events
        WHERE time > NOW() - INTERVAL '7 days'
        GROUP BY day, developer
        ORDER BY day ASC
    """)
    async with AsyncSessionLocal() as session:
        result = await session.execute(sql)
        rows = result.fetchall()

    data = [
        {"day": str(row.day.date()), "developer": row.developer, "commits": int(row.total_commits)}
        for row in rows
    ]
    return {"metrics": data}