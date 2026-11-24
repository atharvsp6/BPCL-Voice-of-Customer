"""
BPCL VoC — Automated Daily Pipeline Runner
============================================
Orchestrates:
  1. Connect to Supabase PostgreSQL
  2. Run all source scrapers (Google Play, App Store, Reddit, YouTube, etc.)
  3. Batch-enrich records through the NLP model
  4. Upsert into the `reviews` table (ON CONFLICT DO NOTHING)
  5. Log a row in `pipeline_runs` for observability

Usage:
  python pipeline/run_daily.py

Required environment variables (set via .env locally or GitHub Secrets in CI):
  SUPABASE_DB_URL   — full PostgreSQL connection URI
                      e.g. postgresql://postgres:<password>@db.<ref>.supabase.co:5432/postgres

Optional API credentials:
  REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT
  YOUTUBE_API_KEY
  TWITTER_USERNAME, TWITTER_PASSWORD
  IG_USERNAME, IG_PASSWORD
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("bpcl_pipeline")

# ---------------------------------------------------------------------------
# Load .env if running locally
# ---------------------------------------------------------------------------
try:
    from dotenv import load_dotenv

    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        logger.info("Loaded environment from .env")
except ImportError:
    pass  # dotenv not installed — env vars must be set externally

# ---------------------------------------------------------------------------
# Add project root to path so pipeline imports work from any cwd
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.ingestion import run_all_scrapers  # noqa: E402
from pipeline.nlp_enricher import enrich_records  # noqa: E402

# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

INSERT_SQL = """
INSERT INTO reviews (
    review_id, source, channel_type, app_name,
    user_name, user_image_url,
    content, processed_text, rating,
    thumbs_up_count, reply_content, replied_at,
    sentiment, sentiment_score, ai_compound, ai_confidence,
    dominant_topic, topic, aspect,
    app_version, raw_metadata, created_at, ingested_at
)
VALUES (
    %(review_id)s, %(source)s, %(channel_type)s, %(app_name)s,
    %(user_name)s, %(user_image_url)s,
    %(content)s, %(processed_text)s, %(rating)s,
    %(thumbs_up_count)s, %(reply_content)s, %(replied_at)s,
    %(sentiment)s, %(sentiment_score)s, %(ai_compound)s, %(ai_confidence)s,
    %(dominant_topic)s, %(topic)s, %(aspect)s,
    %(app_version)s, %(raw_metadata)s, %(created_at)s, NOW()
)
ON CONFLICT (review_id) DO NOTHING;
"""

PIPELINE_RUN_SQL = """
INSERT INTO pipeline_runs (source, records_fetched, records_inserted, status, error_message, duration_seconds)
VALUES (%(source)s, %(records_fetched)s, %(records_inserted)s, %(status)s, %(error_message)s, %(duration_seconds)s);
"""


def _get_connection():
    """Create a psycopg2 connection from SUPABASE_DB_URL."""
    try:
        import psycopg2

        db_url = os.environ.get("SUPABASE_DB_URL", "")
        if not db_url:
            raise ValueError(
                "SUPABASE_DB_URL is not set.\n"
                "Set it in your .env file or as a GitHub Secret.\n"
                "Format: postgresql://postgres:<password>@db.<ref>.supabase.co:5432/postgres"
            )
        conn = psycopg2.connect(db_url, connect_timeout=30)
        conn.autocommit = False
        logger.info("Connected to Supabase PostgreSQL.")
        return conn
    except ImportError:
        logger.critical("psycopg2 not installed. Run: pip install psycopg2-binary")
        sys.exit(1)


def _prepare_record(rec: dict) -> dict:
    """Normalize a raw enriched record into the shape expected by INSERT_SQL."""
    # Ensure all keys exist with safe defaults
    defaults = {
        "review_id": "",
        "source": "unknown",
        "channel_type": "unknown",
        "app_name": None,
        "user_name": None,
        "user_image_url": None,
        "content": "",
        "processed_text": None,
        "rating": None,
        "thumbs_up_count": 0,
        "reply_content": None,
        "replied_at": None,
        "sentiment": "Neutral",
        "sentiment_score": 0.0,
        "ai_compound": 0.0,
        "ai_confidence": 0.0,
        "dominant_topic": None,
        "topic": "General",
        "aspect": "General",
        "app_version": None,
        "raw_metadata": "{}",
        "created_at": datetime.now(tz=timezone.utc),
    }
    merged = {**defaults, **rec}

    # Serialize raw_metadata JSONB
    if isinstance(merged["raw_metadata"], dict):
        merged["raw_metadata"] = json.dumps(merged["raw_metadata"])

    # Coerce numeric types
    if merged["rating"] is not None:
        try:
            merged["rating"] = float(merged["rating"])
        except (TypeError, ValueError):
            merged["rating"] = None

    if merged["sentiment_score"] is not None:
        try:
            merged["sentiment_score"] = float(merged["sentiment_score"])
        except (TypeError, ValueError):
            merged["sentiment_score"] = 0.0

    return merged


def _batch_insert(conn, records: list[dict], source: str) -> int:
    """Insert a batch of records, returning count of rows actually inserted."""
    if not records:
        return 0

    inserted = 0
    with conn.cursor() as cur:
        for rec in records:
            try:
                prepared = _prepare_record(rec)
                cur.execute(INSERT_SQL, prepared)
                if cur.rowcount > 0:
                    inserted += 1
            except Exception as exc:
                logger.error("Insert failed for review_id=%s: %s", rec.get("review_id", "?"), exc)
                conn.rollback()
                # Continue with next record
                continue
        conn.commit()

    return inserted


def _log_pipeline_run(conn, source: str, fetched: int, inserted: int, status: str, error: str, elapsed: float):
    """Write a row to pipeline_runs for observability."""
    try:
        with conn.cursor() as cur:
            cur.execute(
                PIPELINE_RUN_SQL,
                {
                    "source": source,
                    "records_fetched": fetched,
                    "records_inserted": inserted,
                    "status": status,
                    "error_message": error or None,
                    "duration_seconds": round(elapsed, 2),
                },
            )
        conn.commit()
    except Exception as exc:
        logger.warning("Could not log pipeline run for %s: %s", source, exc)


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

def run_pipeline(use_hf_model: bool = True):
    """
    Full pipeline execution:
      1. Connect to DB
      2. Run scrapers
      3. NLP enrich
      4. Upsert to PostgreSQL
      5. Print summary
    """
    pipeline_start = time.time()
    logger.info("=" * 70)
    logger.info("BPCL VoC Daily Pipeline starting at %s", datetime.now(tz=timezone.utc).isoformat())
    logger.info("=" * 70)

    conn = _get_connection()
    summary: dict[str, dict] = {}

    try:
        # ── Step 1: Scrape all sources ──────────────────────────────────────
        logger.info("STEP 1 — Running scrapers…")
        raw_results = run_all_scrapers(conn)

        # ── Step 2: Enrich + Insert per source ─────────────────────────────
        logger.info("STEP 2 — NLP enrichment + DB insert…")
        total_fetched = 0
        total_inserted = 0

        for source, records in raw_results.items():
            source_start = time.time()
            fetched = len(records)
            total_fetched += fetched

            if not records:
                logger.info("[%s] No new records to process.", source.upper())
                summary[source] = {"fetched": 0, "inserted": 0, "status": "empty"}
                continue

            # Enrich
            logger.info("[%s] Enriching %d records…", source.upper(), fetched)
            try:
                enriched = enrich_records(records, use_hf=use_hf_model)
            except Exception as exc:
                logger.error("[%s] NLP enrichment failed: %s", source.upper(), exc)
                enriched = records  # insert raw with neutral defaults

            # Insert
            logger.info("[%s] Inserting into PostgreSQL…", source.upper())
            try:
                inserted = _batch_insert(conn, enriched, source)
                total_inserted += inserted
                elapsed = time.time() - source_start
                _log_pipeline_run(conn, source, fetched, inserted, "success", "", elapsed)
                summary[source] = {"fetched": fetched, "inserted": inserted, "status": "success"}
                logger.info(
                    "[%s] ✓ %d fetched → %d inserted (%.1fs)",
                    source.upper(), fetched, inserted, elapsed,
                )
            except Exception as exc:
                elapsed = time.time() - source_start
                _log_pipeline_run(conn, source, fetched, 0, "failed", str(exc), elapsed)
                summary[source] = {"fetched": fetched, "inserted": 0, "status": "failed"}
                logger.error("[%s] DB insert failed: %s", source.upper(), exc)

    finally:
        conn.close()

    # ── Step 3: Print summary table ─────────────────────────────────────────
    total_elapsed = time.time() - pipeline_start
    logger.info("")
    logger.info("=" * 70)
    logger.info("PIPELINE SUMMARY  (total runtime: %.1fs)", total_elapsed)
    logger.info("=" * 70)
    logger.info("%-20s  %8s  %8s  %10s", "SOURCE", "FETCHED", "INSERTED", "STATUS")
    logger.info("-" * 55)
    for src, stats in summary.items():
        logger.info(
            "%-20s  %8d  %8d  %10s",
            src, stats["fetched"], stats["inserted"], stats["status"],
        )
    logger.info("-" * 55)
    logger.info("%-20s  %8d  %8d", "TOTAL", total_fetched, total_inserted)
    logger.info("=" * 70)

    return summary


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="BPCL VoC Daily Ingestion Pipeline")
    parser.add_argument(
        "--no-hf",
        action="store_true",
        help="Skip HuggingFace model; use VADER only (faster, less accurate)",
    )
    args = parser.parse_args()

    run_pipeline(use_hf_model=not args.no_hf)
