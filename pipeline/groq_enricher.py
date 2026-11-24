"""
BPCL VoC — Groq LLM Aspect & Sentiment Enrichment Module
=========================================================
Leverages Groq's high-speed LPU inference (Llama 3.3 70B / 3.1 8B) for:
  1. Granular BPCL Aspect Classification (LPG, Payments, App Auth, Pump Staff, etc.)
  2. Sub-Aspect & Root Cause Extraction
  3. Continuous Sentiment Scoring (-1.0 to 1.0)
  4. Operational Urgency Detection (High / Normal)
  5. Supabase PostgreSQL Batch Updates

Dual-driver design:
  - Primary: official `groq` SDK (`from groq import Groq`)
  - Resilient Fallback: direct REST HTTP calls via `requests`
    (Guarantees zero crashes even if SDK environment has dependency mismatches)
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Standard BPCL Enterprise Aspect Taxonomy
BPCL_ASPECTS = [
    "LPG Booking & Delivery",
    "Payment & Refunds",
    "App Technical & Authentication",
    "Petrol Pump & Fueling",
    "Staff Behavior & Service",
    "Fuel Quality & Mileage",
    "Rewards & SmartDrive",
    "Customer Support & Grievance",
    "Pricing & Subsidy",
    "App UI & Navigation",
    "General Positive",
    "General Negative",
]

DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"
FAST_GROQ_MODEL = "llama-3.1-8b-instant"


# ---------------------------------------------------------------------------
# API Key Discovery
# ---------------------------------------------------------------------------
def get_groq_api_key(custom_key: Optional[str] = None) -> Optional[str]:
    """
    Discovers Groq API key with waterfall priority:
      1. Explicitly passed custom_key argument
      2. Streamlit session state (if running inside Streamlit)
      3. Streamlit secrets (`st.secrets["GROQ_API_KEY"]`)
      4. OS environment variable (`GROQ_API_KEY`)
      5. Local `.env` file
    """
    if custom_key and custom_key.strip():
        return custom_key.strip()

    # Check Streamlit session_state & secrets safely
    try:
        import streamlit as st

        if hasattr(st, "session_state") and st.session_state.get("groq_api_key"):
            return st.session_state["groq_api_key"].strip()
        if hasattr(st, "secrets") and "GROQ_API_KEY" in st.secrets:
            return st.secrets["GROQ_API_KEY"].strip()
    except Exception:
        pass

    # Check environment variable
    env_key = os.environ.get("GROQ_API_KEY", "").strip()
    if env_key:
        return env_key

    # Check local .env
    try:
        from dotenv import load_dotenv

        candidates = [
            Path(__file__).parent.parent / ".env",
            Path(".env"),
        ]
        for c in candidates:
            if c.exists():
                load_dotenv(c)
                val = os.environ.get("GROQ_API_KEY", "").strip()
                if val:
                    return val
    except Exception:
        pass

    return None


def is_groq_available(custom_key: Optional[str] = None) -> bool:
    """Returns True if a non-empty Groq API key is found."""
    key = get_groq_api_key(custom_key)
    return bool(key and key.startswith("gsk_"))


# ---------------------------------------------------------------------------
# Low-level Groq API Caller (SDK + REST HTTP Fallback)
# ---------------------------------------------------------------------------
def call_groq_chat_completion(
    messages: list[dict],
    api_key: Optional[str] = None,
    model: str = DEFAULT_GROQ_MODEL,
    temperature: float = 0.1,
    json_mode: bool = True,
    max_tokens: int = 2048,
) -> str:
    """
    Calls Groq Chat Completions API with dual execution paths:
    1. Official `groq` Python library
    2. Fallback to `requests.post` REST API endpoint
    """
    resolved_key = get_groq_api_key(api_key)
    if not resolved_key:
        raise ValueError("GROQ_API_KEY not found. Please provide a valid Groq API key.")

    # 1. Attempt official SDK
    try:
        from groq import Groq

        client = Groq(api_key=resolved_key)
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""
    except Exception as sdk_err:
        logger.warning("Groq SDK call failed or unavailable (%s), trying HTTP REST fallback...", sdk_err)

    # 2. Resilient Direct HTTP Fallback
    import requests

    headers = {
        "Authorization": f"Bearer {resolved_key}",
        "Content-Type": "application/json",
    }
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    url = "https://api.groq.com/openai/v1/chat/completions"
    resp = requests.post(url, headers=headers, json=payload, timeout=45)

    if resp.status_code != 200:
        raise RuntimeError(f"Groq API error ({resp.status_code}): {resp.text}")

    data = resp.json()
    return data["choices"][0]["message"]["content"] or ""


# ---------------------------------------------------------------------------
# Single Review Classification
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are an enterprise AI Voice of Customer (VoC) analyst for Bharat Petroleum Corporation Limited (BPCL), including Bharatgas, Hello BPCL app, and BPCL Fuel Retail Outlets.

Analyze the given customer review verbatim and classify it strictly into the standard taxonomy.

Standard BPCL Aspects:
1. "LPG Booking & Delivery" - Bharatgas cylinder booking, delivery delays, distributor issues, delivery boy overcharging/tips, subsidy credit.
2. "Payment & Refunds" - UPI failures, wallet deductions, money debited without booking, refund delays, double deductions.
3. "App Technical & Authentication" - Login failures, OTP not received, app crashes, blank screen, update loops, freezing.
4. "Petrol Pump & Fueling" - Fuel quantity/meter tampering suspicion, short filling, POS machine down, CNG queues, air/water facilities.
5. "Staff Behavior & Service" - Rude pump attendants, refusal of digital payments, delivery boy misconduct, overcharging above MRP.
6. "Fuel Quality & Mileage" - Adulteration suspicion, engine knocking, mileage drop, Speed petrol feedback.
7. "Rewards & SmartDrive" - Missing loyalty points, cashback not credited, voucher redemption errors, UFill QR scanning failure.
8. "Customer Support & Grievance" - Helpline 1800 unresponsive, tickets closed unresolved, no distributor response.
9. "Pricing & Subsidy" - High cylinder price, commercial vs domestic rate disputes, subsidy deduction issues.
10. "App UI & Navigation" - Confusing layout, language options, invoice download issues.
11. "General Positive" - Expressing gratitude, smooth fast service, good app experience.
12. "General Negative" - Vague complaints without specific operational root cause.

Output MUST be a single valid JSON object with EXACTLY these keys:
{
  "aspect": "One of the standard aspects above",
  "sub_aspect": "Concise specific issue (e.g. 'Delivery Boy Tip Demand', 'OTP Timeout', 'UPI Failed Debited')",
  "sentiment": "Positive" | "Neutral" | "Negative",
  "sentiment_score": float between -1.0 (most negative) and 1.0 (most positive),
  "urgency": "High" (financial loss, safety risk, overcharge, or customer escalation) | "Normal",
  "root_cause": "1-sentence executive root cause summary"
}"""


def classify_single_review(
    text: str,
    api_key: Optional[str] = None,
    model: str = DEFAULT_GROQ_MODEL,
) -> dict:
    """
    Classifies a single review verbatim using Groq LLM.
    Returns structured analysis dict.
    """
    if not text or not text.strip():
        return {
            "aspect": "General Negative",
            "sub_aspect": "No Text Provided",
            "sentiment": "Neutral",
            "sentiment_score": 0.0,
            "urgency": "Normal",
            "root_cause": "Empty review content.",
        }

    user_msg = f"Analyze this customer review:\n\n\"\"\"\n{text.strip()[:1000]}\n\"\"\""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_msg},
    ]

    try:
        raw_json = call_groq_chat_completion(messages, api_key=api_key, model=model, temperature=0.1)
        data = json.loads(raw_json)
        # Normalize and validate
        aspect = data.get("aspect", "General Negative")
        if aspect not in BPCL_ASPECTS:
            # Match best substring
            for a in BPCL_ASPECTS:
                if a.lower() in aspect.lower():
                    aspect = a
                    break
            else:
                aspect = "General Negative"

        sentiment = data.get("sentiment", "Neutral")
        if sentiment not in ("Positive", "Neutral", "Negative"):
            sentiment = "Neutral"

        score = float(data.get("sentiment_score", 0.0))
        score = max(-1.0, min(1.0, score))

        return {
            "aspect": aspect,
            "sub_aspect": data.get("sub_aspect", "General Issue"),
            "sentiment": sentiment,
            "sentiment_score": round(score, 4),
            "urgency": data.get("urgency", "Normal"),
            "root_cause": data.get("root_cause", ""),
            "model_used": model,
        }
    except Exception as exc:
        logger.error("Groq single review classification failed: %s", exc)
        return {
            "aspect": "General Negative",
            "sub_aspect": "Analysis Error",
            "sentiment": "Neutral",
            "sentiment_score": 0.0,
            "urgency": "Normal",
            "root_cause": f"Classification error: {exc}",
            "model_used": "fallback",
        }


# ---------------------------------------------------------------------------
# Batch Review Classification (High Throughput)
# ---------------------------------------------------------------------------
BATCH_SYSTEM_PROMPT = """You are an enterprise AI Voice of Customer (VoC) analyst for Bharat Petroleum Corporation Limited (BPCL).
Analyze the batch of customer reviews provided in the user message.

Standard BPCL Aspects:
- "LPG Booking & Delivery"
- "Payment & Refunds"
- "App Technical & Authentication"
- "Petrol Pump & Fueling"
- "Staff Behavior & Service"
- "Fuel Quality & Mileage"
- "Rewards & SmartDrive"
- "Customer Support & Grievance"
- "Pricing & Subsidy"
- "App UI & Navigation"
- "General Positive"
- "General Negative"

Output MUST be a JSON object with a single key "results" containing an array of objects matching the input order:
{
  "results": [
    {
      "id": "review_id passed in input",
      "aspect": "One of the standard aspects",
      "sub_aspect": "Concise specific issue (e.g. 'OTP Delay', 'Tip Demand')",
      "sentiment": "Positive" | "Neutral" | "Negative",
      "sentiment_score": -1.0 to 1.0,
      "urgency": "High" | "Normal",
      "root_cause": "1-sentence executive root cause"
    }
  ]
}"""


def classify_batch_reviews(
    records: list[dict],
    api_key: Optional[str] = None,
    model: str = DEFAULT_GROQ_MODEL,
    batch_size: int = 12,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> list[dict]:
    """
    Classifies a list of review dicts in high-speed batches using Groq LLM.
    Updates records in-place with:
      - 'aspect'
      - 'topic' (set to aspect for consistency)
      - 'sentiment'
      - 'sentiment_score'
      - 'sub_aspect'
      - 'urgency'
      - 'root_cause'

    Includes exponential backoff on HTTP 429 rate limit errors.
    """
    if not records:
        return records

    resolved_key = get_groq_api_key(api_key)
    if not resolved_key:
        raise ValueError("Cannot run batch classification: GROQ_API_KEY is not set.")

    total = len(records)
    logger.info("Starting Groq LLM batch classification for %d records (batch_size=%d)...", total, batch_size)

    for start_idx in range(0, total, batch_size):
        end_idx = min(start_idx + batch_size, total)
        batch = records[start_idx:end_idx]

        items_payload = []
        for r in batch:
            r_id = str(r.get("review_id", f"idx_{start_idx}"))
            text = str(r.get("content", "") or r.get("processed_text", "")).strip()
            items_payload.append({"id": r_id, "text": text[:500]})

        user_content = json.dumps(items_payload, ensure_ascii=False)
        messages = [
            {"role": "system", "content": BATCH_SYSTEM_PROMPT},
            {"role": "user", "content": f"Classify these {len(items_payload)} BPCL reviews:\n{user_content}"},
        ]

        # Call with retry on rate limit
        max_retries = 3
        backoff = 2.0
        success = False

        for attempt in range(max_retries):
            try:
                raw_json = call_groq_chat_completion(messages, api_key=resolved_key, model=model, temperature=0.1)
                data = json.loads(raw_json)
                results_list = data.get("results", [])

                # Map results by ID
                results_by_id = {str(item.get("id")): item for item in results_list if isinstance(item, dict)}

                for rec in batch:
                    rec_id = str(rec.get("review_id", ""))
                    analysis = results_by_id.get(rec_id)
                    if analysis:
                        aspect = analysis.get("aspect", "General Negative")
                        if aspect not in BPCL_ASPECTS:
                            for a in BPCL_ASPECTS:
                                if a.lower() in aspect.lower():
                                    aspect = a
                                    break
                            else:
                                aspect = "General Negative"

                        sent = analysis.get("sentiment", "Neutral")
                        if sent not in ("Positive", "Neutral", "Negative"):
                            sent = "Neutral"

                        score = float(analysis.get("sentiment_score", 0.0))
                        score = round(max(-1.0, min(1.0, score)), 4)

                        rec["aspect"] = aspect
                        rec["topic"] = aspect
                        rec["sentiment"] = sent
                        rec["sentiment_score"] = score
                        rec["sub_aspect"] = analysis.get("sub_aspect", "")
                        rec["urgency"] = analysis.get("urgency", "Normal")
                        rec["root_cause"] = analysis.get("root_cause", "")
                        rec["groq_enriched"] = True
                success = True
                break
            except Exception as exc:
                logger.warning("Batch %d-%d attempt %d failed: %s", start_idx, end_idx, attempt + 1, exc)
                time.sleep(backoff)
                backoff *= 2

        if not success:
            logger.error("Failed to process batch %d-%d with Groq. Skipping batch.", start_idx, end_idx)

        if progress_callback:
            progress_callback(end_idx, total, f"Classified {end_idx}/{total} reviews with Groq LLM ({model})")

    logger.info("Groq batch classification completed for %d records.", total)
    return records


# ---------------------------------------------------------------------------
# Supabase PostgreSQL Bulk Updater
# ---------------------------------------------------------------------------
UPDATE_REVIEW_ASPECT_SQL = """
UPDATE reviews
SET aspect = %(aspect)s,
    topic = %(topic)s,
    sentiment = %(sentiment)s,
    sentiment_score = %(sentiment_score)s,
    raw_metadata = jsonb_set(
        COALESCE(raw_metadata, '{}'::jsonb),
        '{groq_enrichment}',
        %(groq_data)s::jsonb
    )
WHERE review_id = %(review_id)s;
"""


def update_supabase_aspects(
    db_connection_or_url: Any,
    records: list[dict],
) -> int:
    """
    Updates the Supabase `reviews` table with Groq-classified aspects and sentiment.
    Returns the count of rows successfully updated.
    """
    if not records:
        return 0

    import psycopg2

    should_close = False
    if isinstance(db_connection_or_url, str):
        conn = psycopg2.connect(db_connection_or_url)
        should_close = True
    else:
        conn = db_connection_or_url

    updated_count = 0
    try:
        with conn.cursor() as cur:
            for r in records:
                if not r.get("review_id"):
                    continue
                groq_payload = {
                    "aspect": r.get("aspect"),
                    "sub_aspect": r.get("sub_aspect"),
                    "urgency": r.get("urgency"),
                    "root_cause": r.get("root_cause"),
                    "enriched_at": datetime.now(tz=timezone.utc).isoformat(),
                }
                params = {
                    "review_id": r["review_id"],
                    "aspect": r.get("aspect", "General"),
                    "topic": r.get("topic", r.get("aspect", "General")),
                    "sentiment": r.get("sentiment", "Neutral"),
                    "sentiment_score": float(r.get("sentiment_score", 0.0)),
                    "groq_data": json.dumps(groq_payload),
                }
                try:
                    cur.execute(UPDATE_REVIEW_ASPECT_SQL, params)
                    if cur.rowcount > 0:
                        updated_count += 1
                except Exception as row_err:
                    logger.warning("Failed updating review_id=%s: %s", r["review_id"], row_err)
            conn.commit()
    finally:
        if should_close:
            conn.close()

    return updated_count
