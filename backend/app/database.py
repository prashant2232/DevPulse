from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from app.config import settings

_engine = None
_session_factory = None


def _get_engine():
    global _engine
    if _engine is None:
        _engine = create_async_engine(settings.timescale_url, echo=False)
    return _engine


def AsyncSessionLocal():
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(
            _get_engine(), class_=AsyncSession, expire_on_commit=False
        )
    return _session_factory()


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS commit_events (
    time         TIMESTAMPTZ NOT NULL,
    developer    TEXT NOT NULL,
    repo         TEXT NOT NULL,
    event_type   TEXT NOT NULL,
    commit_count INT DEFAULT 1
);
"""

CREATE_HYPERTABLE_SQL = """
SELECT create_hypertable('commit_events', 'time', if_not_exists => TRUE);
"""


async def init_db():
    async with _get_engine().begin() as conn:
        await conn.execute(text(CREATE_TABLE_SQL))
        try:
            await conn.execute(text(CREATE_HYPERTABLE_SQL))
        except Exception as e:
            print("Hypertable skipped:", e)
    print("✅ TimescaleDB initialized")


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session