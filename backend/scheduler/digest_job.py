import json
import logging
from datetime import datetime, timezone

from sqlalchemy import text
from groq import Groq
from pydantic import ValidationError

from app.config import settings
from app.database import AsyncSessionLocal
from app.redis_client import get_redis
from app.models import DigestReport

logger = logging.getLogger(__name__)


async def generate_weekly_digest():
    logger.info("Starting weekly digest generation...")

    # ── 1. Fetch data ─────────────────────────────────────────────────────────
    sql = text("""
        SELECT
            developer,
            SUM(commit_count)  AS total_commits,
            MAX(time)          AS last_active
        FROM commit_events
        WHERE time > NOW() - INTERVAL '7 days'
        GROUP BY developer
        ORDER BY total_commits DESC
    """)

    high_volume_sql = text("""
        SELECT developer, repo, commit_count, time
        FROM commit_events
        WHERE time > NOW() - INTERVAL '7 days'
          AND commit_count > 15
        ORDER BY commit_count DESC
        LIMIT 10
    """)

    async with AsyncSessionLocal() as session:
        result      = await session.execute(sql)
        devs        = result.fetchall()
        alert_result = await session.execute(high_volume_sql)
        suspicious  = alert_result.fetchall()

    if not devs:
        logger.info("No commit data for past 7 days — skipping digest")
        return

    # ── 2. Build prompt ───────────────────────────────────────────────────────
    dev_summary = "\n".join(
        f"- {r.developer}: {int(r.total_commits)} commits, "
        f"last active {r.last_active.strftime('%Y-%m-%d %H:%M UTC')}"
        for r in devs
    )

    suspicious_summary = (
        "\n".join(
            f"- {r.developer} pushed {r.commit_count} commits to {r.repo} "
            f"at {r.time.strftime('%Y-%m-%d %H:%M UTC')}"
            for r in suspicious
        )
        if suspicious else "None detected."
    )

    prompt = f"""You are a software engineering team health analyst.
Analyse this GitHub commit data for the past 7 days and return a JSON object.

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

    # ── 3. Call Groq ──────────────────────────────────────────────────────────
    if not settings.groq_api_key:
        logger.error("GROQ_API_KEY not set — skipping digest")
        return

    try:
        client = Groq(api_key=settings.groq_api_key)
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=512,
        )
        raw_text = response.choices[0].message.content.strip()
        logger.info(f"Groq response: {raw_text[:200]}")
    except Exception as e:
        logger.error(f"Groq API error: {e}")
        return

    # ── 4. Parse and validate ─────────────────────────────────────────────────
    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
        raw_text = raw_text.strip()

    try:
        data   = json.loads(raw_text)
        report = DigestReport(**data)
    except (json.JSONDecodeError, ValidationError) as e:
        logger.error(f"Failed to parse Groq response: {e}\nRaw: {raw_text}")
        return

    # ── 5. Store in Redis ─────────────────────────────────────────────────────
    r = get_redis()
    await r.set("weekly_digest", report.model_dump_json(), ex=86400 * 7)
    logger.info("Weekly digest stored in Redis")


async def trigger_digest_now():
    await generate_weekly_digest()