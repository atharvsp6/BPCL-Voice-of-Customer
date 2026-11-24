"""
BPCL VoC — NLP Enrichment Pipeline
=====================================
Enriches raw review records with:
  1. Sentiment  → Positive / Neutral / Negative + score (-1.0 to 1.0)
  2. Topic      → Business-vertical label (e.g. "LPG Delivery", "App Bugs")
  3. Aspect     → Primary customer pain-point label

Sentiment model priority:
  A. HuggingFace `cardiffnlp/twitter-roberta-base-sentiment-latest`
     (CPU-compatible, ~125 MB download, cached after first run)
  B. VADER lexicon fallback (zero-dependency, instant)

Topic/Aspect classification:
  - Rule-based keyword matching using topic_keywords.json
  - Extended BPCL-specific business vertical mapping
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Topic & Aspect keyword maps
# ---------------------------------------------------------------------------

# Default BPCL business verticals — merged with topic_keywords.json at runtime
DEFAULT_TOPIC_KEYWORDS: dict[str, list[str]] = {
    "App Bugs / OTP Issues": [
        "otp", "login", "crash", "freeze", "error", "bug", "not working",
        "open", "loading", "blank screen", "app down", "update fail",
    ],
    "Payment / UPI Failure": [
        "payment", "upi", "transaction", "failed", "money", "account", "bank",
        "recharge", "wallet", "refund", "deducted", "charged twice",
    ],
    "SmartDrive / Rewards": [
        "reward", "point", "smartdrive", "redeem", "offer", "cashback",
        "discount", "loyalty", "voucher", "coupon",
    ],
    "LPG Delivery": [
        "lpg", "gas", "cylinder", "booking", "delivery", "bharatgas",
        "domestic", "subsidy", "refill", "new connection",
    ],
    "Petrol Pump Staff": [
        "staff", "attendant", "pump", "filling", "petrol station",
        "misbehave", "rude", "overcharge", "short fill", "nozzle",
    ],
    "Fuel Quality": [
        "fuel", "quality", "petrol", "diesel", "speed", "purity",
        "adulterated", "water", "contaminated", "mileage", "performance",
    ],
    "App Navigation / UI": [
        "ui", "interface", "design", "button", "slow", "feature", "usability",
        "user friendly", "confusing", "navigation", "menu",
    ],
    "Customer Support": [
        "support", "helpline", "customer care", "complaint", "response",
        "resolve", "ticket", "callback", "chat", "1800",
    ],
    "UFill / Self-Service": [
        "ufill", "self service", "nozzle", "fill yourself", "no attendant",
    ],
    "General Positive": [
        "great", "excellent", "amazing", "love", "best", "good", "happy",
        "smooth", "fast", "quick", "perfect", "awesome", "satisfied",
    ],
}

ASPECT_MAP: dict[str, list[str]] = {
    "App Performance": ["crash", "freeze", "slow", "lag", "loading", "hang"],
    "Authentication": ["otp", "login", "logout", "password", "verify", "2fa"],
    "Payments": ["payment", "upi", "transaction", "wallet", "refund", "bank"],
    "Rewards": ["reward", "point", "loyalty", "cashback", "redeem"],
    "Fuel Quality": ["fuel", "quality", "petrol", "diesel", "mileage"],
    "LPG Service": ["lpg", "gas", "cylinder", "delivery", "booking"],
    "Staff Behaviour": ["staff", "attendant", "rude", "helpful", "behaviour"],
    "Customer Support": ["support", "helpline", "complaint", "resolve"],
    "App UI / UX": ["ui", "interface", "design", "navigation", "button"],
    "General": [],  # catch-all
}


def _load_topic_keywords(json_path: Optional[str] = None) -> dict[str, list[str]]:
    """Load topic keywords from JSON, merging with defaults."""
    keywords = dict(DEFAULT_TOPIC_KEYWORDS)

    if json_path is None:
        # Look in repo root (works from pipeline/ subdir too)
        candidates = [
            Path(__file__).parent.parent / "topic_keywords.json",
            Path("topic_keywords.json"),
        ]
        for c in candidates:
            if c.exists():
                json_path = str(c)
                break

    if json_path and Path(json_path).exists():
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            neg_topics = data.get("negative_topics", {})
            # Map numeric keys to labels
            numeric_label_map = {
                "1": "App Bugs / OTP Issues",
                "2": "Payment / UPI Failure",
                "3": "App Navigation / UI",
                "4": "SmartDrive / Rewards",
            }
            for key, kws in neg_topics.items():
                label = numeric_label_map.get(str(key), f"Topic {key}")
                if label in keywords:
                    keywords[label] = list(set(keywords[label] + kws))
                else:
                    keywords[label] = kws
        except Exception as exc:
            logger.warning("Could not load topic_keywords.json: %s", exc)

    return keywords


TOPIC_KEYWORDS = _load_topic_keywords()


# ---------------------------------------------------------------------------
# Sentiment Model — HuggingFace with VADER fallback
# ---------------------------------------------------------------------------

_hf_pipeline = None  # lazy singleton


def _load_hf_model():
    """Load HuggingFace RoBERTa sentiment model (lazy, cached after first call)."""
    global _hf_pipeline
    if _hf_pipeline is not None:
        return _hf_pipeline
    try:
        from transformers import pipeline as hf_pipeline

        logger.info("Loading HuggingFace sentiment model (first run may download ~125 MB)…")
        _hf_pipeline = hf_pipeline(
            "sentiment-analysis",
            model="cardiffnlp/twitter-roberta-base-sentiment-latest",
            tokenizer="cardiffnlp/twitter-roberta-base-sentiment-latest",
            device=-1,          # CPU only (free tier safe)
            max_length=512,
            truncation=True,
            top_k=None,         # returns all labels with scores
        )
        logger.info("HuggingFace model loaded successfully.")
        return _hf_pipeline
    except Exception as exc:
        logger.warning("HuggingFace model unavailable: %s — using VADER fallback.", exc)
        return None


def _vader_sentiment(text: str) -> tuple[str, float, float]:
    """VADER-based sentiment. Returns (label, score, compound)."""
    try:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

        sia = SentimentIntensityAnalyzer()
        scores = sia.polarity_scores(text)
        compound = scores["compound"]
        if compound >= 0.05:
            label = "Positive"
        elif compound <= -0.05:
            label = "Negative"
        else:
            label = "Neutral"
        # Normalize compound (-1,1) to sentiment_score
        return label, compound, compound
    except ImportError:
        logger.error("vaderSentiment not installed. Run: pip install vaderSentiment")
        return "Neutral", 0.0, 0.0


# RoBERTa label mapping  (model outputs: 'positive', 'neutral', 'negative')
_ROBERTA_LABEL_MAP = {
    "positive": "Positive",
    "neutral": "Neutral",
    "negative": "Negative",
    "label_0": "Negative",
    "label_1": "Neutral",
    "label_2": "Positive",
}


def _hf_sentiment(text: str, pipe) -> tuple[str, float, float]:
    """HuggingFace RoBERTa sentiment. Returns (label, score, compound_equiv)."""
    try:
        # Truncate to 512 chars for speed (tokenizer handles true tokens)
        result = pipe(text[:512])
        if isinstance(result, list) and len(result) > 0:
            # top_k=None returns a list of dicts per input
            scores_list = result[0] if isinstance(result[0], list) else result
            best = max(scores_list, key=lambda x: x["score"])
            raw_label = best["label"].lower()
            label = _ROBERTA_LABEL_MAP.get(raw_label, "Neutral")
            confidence = round(best["score"], 4)
            # Build compound: pos_score - neg_score
            score_dict = {_ROBERTA_LABEL_MAP.get(x["label"].lower(), "Neutral"): x["score"] for x in scores_list}
            compound = round(score_dict.get("Positive", 0.0) - score_dict.get("Negative", 0.0), 4)
            return label, confidence, compound
    except Exception as exc:
        logger.warning("HuggingFace inference failed: %s", exc)
    return "Neutral", 0.5, 0.0


def get_sentiment(text: str, use_hf: bool = True) -> dict:
    """
    Returns sentiment dict with keys:
      sentiment       : str   ('Positive' | 'Neutral' | 'Negative')
      sentiment_score : float (-1.0 to 1.0)
      ai_confidence   : float (0.0 to 1.0)
      ai_compound     : float
    """
    if not text or not isinstance(text, str):
        return {"sentiment": "Neutral", "sentiment_score": 0.0, "ai_confidence": 0.0, "ai_compound": 0.0}

    clean = text.strip()

    if use_hf:
        pipe = _load_hf_model()
        if pipe:
            label, confidence, compound = _hf_sentiment(clean, pipe)
            return {
                "sentiment": label,
                "sentiment_score": compound,
                "ai_confidence": confidence,
                "ai_compound": compound,
            }

    # VADER fallback
    label, score, compound = _vader_sentiment(clean)
    return {
        "sentiment": label,
        "sentiment_score": score,
        "ai_confidence": abs(compound),
        "ai_compound": compound,
    }


# ---------------------------------------------------------------------------
# Topic Classification
# ---------------------------------------------------------------------------

def _preprocess(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9 ]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def classify_topic(text: str, topic_keywords: Optional[dict] = None) -> str:
    """
    Keyword-based topic classification.
    Returns the best-matching topic label (most keyword hits).
    """
    kws = topic_keywords or TOPIC_KEYWORDS
    clean = _preprocess(text)
    best_topic = "General"
    best_hits = 0

    for topic, keywords in kws.items():
        if not keywords:
            continue
        hits = sum(1 for kw in keywords if kw in clean)
        if hits > best_hits:
            best_hits = hits
            best_topic = topic

    return best_topic


def classify_aspect(text: str) -> str:
    """
    Keyword-based aspect classification.
    Returns the primary customer aspect label.
    """
    clean = _preprocess(text)
    best_aspect = "General"
    best_hits = 0

    for aspect, keywords in ASPECT_MAP.items():
        if not keywords:
            continue
        hits = sum(1 for kw in keywords if kw in clean)
        if hits > best_hits:
            best_hits = hits
            best_aspect = aspect

    return best_aspect


# ---------------------------------------------------------------------------
# Text pre-processing
# ---------------------------------------------------------------------------

def preprocess_text(text: str) -> str:
    """Clean review text for NLP inference."""
    if not text:
        return ""
    # Remove URLs
    text = re.sub(r"https?://\S+", " ", text)
    # Remove @mentions and #hashtags (keep content)
    text = re.sub(r"[@#]\w+", " ", text)
    # Remove emojis (basic range)
    text = re.sub(r"[^\x00-\x7F]+", " ", text)
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ---------------------------------------------------------------------------
# Main enrichment function
# ---------------------------------------------------------------------------

def enrich_records(
    records: list[dict],
    use_hf: bool = True,
    use_groq: bool = True,
    groq_api_key: Optional[str] = None,
    topic_keywords: Optional[dict] = None,
    batch_size: int = 32,
) -> list[dict]:
    """
    Enriches a list of raw review dicts with NLP fields:
      - processed_text
      - sentiment, sentiment_score, ai_confidence, ai_compound
      - topic, aspect

    If Groq API key is available and use_groq=True, uses Groq LLM (Llama 3.3 70B)
    for high-precision aspect classification & root cause extraction.
    Otherwise falls back seamlessly to RoBERTa/VADER + keyword matching.

    Returns the same list with fields added in-place.
    """
    if not records:
        return records

    # 1. Check if Groq LLM is available for aspect enrichment
    groq_active = False
    if use_groq:
        try:
            from pipeline.groq_enricher import is_groq_available, classify_batch_reviews
            if is_groq_available(groq_api_key):
                groq_active = True
                logger.info("Groq LLM detected — will use Groq for aspect categorization & root cause.")
        except Exception as groq_chk_err:
            logger.debug("Groq check failed: %s", groq_chk_err)

    kws = topic_keywords or TOPIC_KEYWORDS

    # Lazy-load model once for the whole batch (for sentiment if Groq not used or as fallback)
    pipe = None
    if use_hf and not groq_active:
        pipe = _load_hf_model()

    total = len(records)
    logger.info("NLP enrichment: %d records (Groq=%s, HuggingFace=%s)", total, groq_active, pipe is not None)

    for i, rec in enumerate(records):
        try:
            raw_text = rec.get("content", "") or ""
            clean = preprocess_text(raw_text)
            rec["processed_text"] = clean

            # Sentiment (Base)
            if pipe:
                label, confidence, compound = _hf_sentiment(clean, pipe)
            else:
                label, confidence, compound = _vader_sentiment(clean)
                confidence = abs(compound)

            rec["sentiment"] = label
            rec["sentiment_score"] = round(compound, 4)
            rec["ai_confidence"] = round(confidence, 4)
            rec["ai_compound"] = round(compound, 4)

            # Topic & Aspect (Keyword baseline)
            rec["topic"] = classify_topic(raw_text, kws)
            rec["aspect"] = classify_aspect(raw_text)

        except Exception as exc:
            logger.error("Enrichment failed for record %d (review_id=%s): %s", i, rec.get("review_id", "?"), exc)
            # Safe defaults so the record can still be inserted
            rec.setdefault("processed_text", "")
            rec.setdefault("sentiment", "Neutral")
            rec.setdefault("sentiment_score", 0.0)
            rec.setdefault("ai_confidence", 0.0)
            rec.setdefault("ai_compound", 0.0)
            rec.setdefault("topic", "General")
            rec.setdefault("aspect", "General")

        if (i + 1) % 100 == 0:
            logger.info("  Enriched %d / %d records…", i + 1, total)

    # 2. If Groq is active, elevate aspect classification with Llama 3.3 70B
    if groq_active:
        try:
            from pipeline.groq_enricher import classify_batch_reviews
            records = classify_batch_reviews(records, api_key=groq_api_key)
            logger.info("Groq LLM aspect categorization successfully applied to %d records.", total)
        except Exception as groq_err:
            logger.warning("Groq batch categorization encountered error (%s) — retained baseline NLP.", groq_err)

    logger.info("NLP enrichment complete: %d records processed.", total)
    return records
