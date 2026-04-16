import json
import logging
import os
from datetime import datetime, timezone

from sqlalchemy import text
import google.generativeai as genai
from pydantic import ValidationError

from app.config import settings
from app.database import AsyncSessionLocal
from app.redis_client import get_redis
from app.models import DigestReport

logger = logging.getLogger(__name__)


async def generate_weekly_digest():
    """
    1. Query last 7 days of commit activity from TimescaleDB
    2. Build a structured prompt
    3. Call Gemini Pro
    4. Validate response with Pydantic
    5. Store in Redis with 7-day TTL
    """
    logger.info("🔄 Starting weekly digest generation...")

    # ── 1. Fetch data from TimescaleDB ────────────────────────────────────────
    sql = text("""
        SELECT
            developer,
            SUM(commit_count)                          AS total_commits,
            COUNT(*)                                   AS event_count,
            MAX(time)                                  AS last_active
        FROM commit_events
        WHERE time > NOW() - INTERVAL '7 days'
        GROUP BY developer
        ORDER BY total_commits DESC
    """)

    alert_sql = text("""
        SELECT developer, repo, event_type, time
        FROM commit_events
        WHERE time > NOW() - INTERVAL '7 days'
          AND commit_count > 15
        ORDER BY commit_count DESC
        LIMIT 10
    """)

    async with AsyncSessionLocal() as session:
        result = await session.execute(sql)
        devs = result.fetchall()

        alert_result = await session.execute(alert_sql)
        suspicious = alert_result.fetchall()

    if not devs:
        logger.info("No commit data for the past 7 days — skipping digest")
        return

    # ── 2. Build prompt ───────────────────────────────────────────────────────
    dev_summary = "\n".join(
        f"- {row.developer}: {int(row.total_commits)} commits, "
        f"last active {row.last_active.strftime('%Y-%m-%d %H:%M UTC')}"
        for row in devs
    )

    suspicious_summary = (
        "\n".join(
            f"- {row.developer} pushed {row.event_type} to {row.repo} at "
            f"{row.time.strftime('%Y-%m-%d %H:%M UTC')}"
            for row in suspicious
        )
        if suspicious
        else "None detected."
    )

    prompt = f"""You are a software engineering team health analyst.
Analyse the following GitHub commit data for the past 7 days and return a JSON object.

DEVELOPER ACTIVITY:
{dev_summary}

SUSPICIOUS HIGH-VOLUME EVENTS:
{suspicious_summary}

Return ONLY a valid JSON object with exactly these three keys (no markdown, no explanation):
{{
  "summary": "2-3 sentences summarising overall team activity and productivity",
  "anomaly_note": "1-2 sentences about any suspicious patterns or unusual commit spikes",
  "recommendation": "1 concrete actionable recommendation for the team next week"
}}"""

    # ── 3. Call Gemini Pro ────────────────────────────────────────────────────
    try:
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)
        raw_text = response.text.strip()
        logger.info(f"Gemini raw response: {raw_text[:200]}")
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        return

    # ── 4. Parse and validate ─────────────────────────────────────────────────
    # Strip markdown code fences if Gemini wraps the JSON anyway
    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
        raw_text = raw_text.strip()

    try:
        data = json.loads(raw_text)
        report = DigestReport(**data)
    except (json.JSONDecodeError, ValidationError) as e:
        logger.error(f"Failed to parse Gemini response: {e}\nRaw: {raw_text}")
        return

    # ── 5. Store in Redis with 7-day TTL ──────────────────────────────────────
    r = get_redis()
    await r.set("weekly_digest", report.model_dump_json(), ex=86400 * 7)
    logger.info("✅ Weekly digest stored in Redis")


async def trigger_digest_now():
    """
    Helper you can call manually to test without waiting for Monday.
    Hit: POST /api/digest/trigger (added below in main.py)
    """
    await generate_weekly_digest()