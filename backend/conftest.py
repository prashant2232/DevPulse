import os
import pytest

# Set these BEFORE any app module is imported.
# This prevents database.py / config.py from getting empty strings.
os.environ.setdefault("TIMESCALE_URL", "postgresql+asyncpg://user:pass@localhost:5432/testdb")
os.environ.setdefault("REDIS_URL",     "redis://localhost:6379")
os.environ.setdefault("KAFKA_BOOTSTRAP", "localhost:9092")
os.environ.setdefault("GEMINI_API_KEY",  "test-key")
os.environ.setdefault("WEBHOOK_SECRET",  "test-secret")