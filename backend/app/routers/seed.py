from fastapi import APIRouter
from sqlalchemy import text
from app.database import AsyncSessionLocal

router = APIRouter()

@router.post("/api/dev/seed-history")
async def seed_history():
    """Inserts 7 days of historical commit data with real team names."""

    data = [
        # (developer, days_ago, commit_count)
        # Nidhi — steady contributor
        ("Nidhi", 7, 5), ("Nidhi", 6, 3), ("Nidhi", 5, 7),
        ("Nidhi", 4, 4), ("Nidhi", 3, 6), ("Nidhi", 2, 5), ("Nidhi", 1, 8),

        # Kshitij — high output, one anomaly spike
        ("Kshitij", 7, 4), ("Kshitij", 6, 6), ("Kshitij", 5, 3),
        ("Kshitij", 4, 28), ("Kshitij", 3, 5), ("Kshitij", 2, 7), ("Kshitij", 1, 6),

        # Pallavi — consistent mid-level
        ("Pallavi", 7, 3), ("Pallavi", 6, 5), ("Pallavi", 5, 4),
        ("Pallavi", 4, 6), ("Pallavi", 3, 3), ("Pallavi", 2, 5), ("Pallavi", 1, 7),

        # Abhishek — slow start, picks up pace
        ("Abhishek", 7, 2), ("Abhishek", 6, 2), ("Abhishek", 5, 4),
        ("Abhishek", 4, 5), ("Abhishek", 3, 6), ("Abhishek", 2, 8), ("Abhishek", 1, 9),

        # Prachi — anomaly on day 2 (late night push)
        ("Prachi", 7, 4), ("Prachi", 6, 3), ("Prachi", 5, 5),
        ("Prachi", 4, 4), ("Prachi", 3, 6), ("Prachi", 2, 30), ("Prachi", 1, 5),
    ]

    async with AsyncSessionLocal() as session:
        for developer, days_ago, commit_count in data:
            await session.execute(
                text(
                    "INSERT INTO commit_events "
                    "(time, developer, repo, event_type, commit_count) "
                    "VALUES ("
                    f"NOW() - INTERVAL '{days_ago} days', "
                    ":developer, 'org/devpulse', 'push', :commit_count)"
                ),
                {"developer": developer, "commit_count": commit_count},
            )
        await session.commit()

    return {"status": "ok", "rows_inserted": len(data)}