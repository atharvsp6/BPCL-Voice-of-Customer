"""
BPCL Customer Intelligence Platform
=====================================
Enterprise-grade Voice of Customer analytics dashboard for
Bharat Petroleum Corporation Limited.

Sources: Google Play · Apple App Store · YouTube · Consumer Forum · Reddit
Data: Live Supabase PostgreSQL + 100k historical CSV fallback

Launch: streamlit run 03_dashboard.py
"""

import json
import re
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional


import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

# Groq LLM Aspect & Sentiment Analysis
try:
    from pipeline.groq_enricher import (
        BPCL_ASPECTS,
        DEFAULT_GROQ_MODEL,
        FAST_GROQ_MODEL,
        classify_batch_reviews,
        classify_single_review,
        get_groq_api_key,
        is_groq_available,
        update_supabase_aspects,
    )
except Exception:
    BPCL_ASPECTS = [
        "LPG Booking & Delivery", "Payment & Refunds", "App Technical & Authentication",
        "Petrol Pump & Fueling", "Staff Behavior & Service", "Fuel Quality & Mileage",
        "Rewards & SmartDrive", "Customer Support & Grievance", "Pricing & Subsidy",
        "App UI & Navigation", "General Positive", "General Negative"
    ]
    DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"
    FAST_GROQ_MODEL = "llama-3.1-8b-instant"
    def get_groq_api_key(k=None): return None
    def is_groq_available(k=None): return False
    def classify_single_review(*a, **k): return {}
    def classify_batch_reviews(r, *a, **k): return r
    def update_supabase_aspects(*a, **k): return 0


# =============================================================================
# PAGE CONFIG  — must be first Streamlit call
# =============================================================================
st.set_page_config(
    page_title="BPCL Customer Intelligence Platform",
    page_icon="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>▣</text></svg>",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================================================================
# BRAND DESIGN SYSTEM
# =============================================================================
BRAND = {
    "navy":        "#002D62",
    "navy_mid":    "#003D82",
    "navy_light":  "#004DAA",
    "gold":        "#F5A623",
    "gold_light":  "#F9C06A",
    "positive":    "#10B981",
    "positive_bg": "#D1FAE5",
    "negative":    "#EF4444",
    "negative_bg": "#FEE2E2",
    "neutral":     "#64748B",
    "neutral_bg":  "#F1F5F9",
    "white":       "#FFFFFF",
    "bg":          "#F8FAFC",
    "card":        "#FFFFFF",
    "border":      "#E2E8F0",
    "border_mid":  "#CBD5E1",
    "text_primary":"#0F172A",
    "text_secondary":"#475569",
    "text_muted":  "#94A3B8",
    "plot_bg":     "#FFFFFF",
    "grid":        "rgba(226,232,240,0.8)",
}

SOURCE_CONFIG = {
    "google_play":    {"label": "Google Play",    "color": "#01875F", "icon": "fa-brands fa-google-play"},
    "app_store":      {"label": "App Store",      "color": "#000000", "icon": "fa-brands fa-apple"},
    "youtube":        {"label": "YouTube",         "color": "#FF0000", "icon": "fa-brands fa-youtube"},
    "consumer_forum": {"label": "Consumer Forum",  "color": "#6366F1", "icon": "fa-solid fa-comments"},
    "reddit":         {"label": "Reddit",          "color": "#FF4500", "icon": "fa-brands fa-reddit"},
    "twitter":        {"label": "Twitter / X",     "color": "#1D9BF0", "icon": "fa-brands fa-x-twitter"},
    "instagram":      {"label": "Instagram",       "color": "#E1306C", "icon": "fa-brands fa-instagram"},
    "csv":            {"label": "Historical CSV",  "color": BRAND["navy"], "icon": "fa-solid fa-database"},
}

# =============================================================================
# GLOBAL CSS + FONTAWESOME
# =============================================================================
def inject_global_css():
    st.markdown(
        f"""
        <link rel="stylesheet"
              href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css"
              crossorigin="anonymous" referrerpolicy="no-referrer" />
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap"
              rel="stylesheet">

        <style>
        /* ── Reset & base ──────────────────────────────────────────── */
        *, *::before, *::after {{ box-sizing: border-box; }}

        html, body, .stApp {{
            font-family: 'Inter', system-ui, -apple-system, sans-serif !important;
            background-color: {BRAND['bg']} !important;
            color: {BRAND['text_primary']} !important;
        }}

        .main .block-container {{
            padding: 1.5rem 2rem 3rem !important;
            max-width: 1600px !important;
        }}

        /* ── Sidebar ──────────────────────────────────────────────── */
        section[data-testid="stSidebar"] {{
            background: {BRAND['navy']} !important;
            border-right: none !important;
        }}
        section[data-testid="stSidebar"] > div {{
            background: transparent !important;
        }}
        div[data-testid="stSidebarContent"] *,
        div[data-testid="stSidebarContent"] p,
        div[data-testid="stSidebarContent"] label,
        div[data-testid="stSidebarContent"] span,
        div[data-testid="stSidebarContent"] div {{
            color: rgba(255,255,255,0.90) !important;
        }}
        div[data-testid="stSidebarContent"] h1,
        div[data-testid="stSidebarContent"] h2,
        div[data-testid="stSidebarContent"] h3 {{
            color: #FFFFFF !important;
            font-weight: 700 !important;
        }}
        div[data-testid="stSidebarContent"] hr {{
            border-color: rgba(255,255,255,0.15) !important;
        }}
        div[data-testid="stSidebarContent"] div[data-baseweb="input"],
        div[data-testid="stSidebarContent"] div[data-baseweb="base-input"],
        div[data-testid="stSidebarContent"] div[data-baseweb="textarea"] {{
            background: rgba(255,255,255,0.12) !important;
            border: 1.5px solid rgba(255,255,255,0.25) !important;
            border-radius: 8px !important;
        }}
        div[data-testid="stSidebarContent"] div[data-baseweb="input"]:focus-within,
        div[data-testid="stSidebarContent"] div[data-baseweb="base-input"]:focus-within {{
            border-color: {BRAND['gold']} !important;
            box-shadow: 0 0 0 2px rgba(245,166,35,0.3) !important;
        }}
        div[data-testid="stSidebarContent"] input,
        div[data-testid="stSidebarContent"] textarea {{
            color: #FFFFFF !important;
            -webkit-text-fill-color: #FFFFFF !important;
            background: transparent !important;
            font-size: 0.88rem !important;
            font-weight: 500 !important;
            caret-color: {BRAND['gold']} !important;
        }}
        div[data-testid="stSidebarContent"] input::placeholder,
        div[data-testid="stSidebarContent"] textarea::placeholder {{
            color: rgba(255,255,255,0.55) !important;
            -webkit-text-fill-color: rgba(255,255,255,0.55) !important;
        }}
        div[data-testid="stSidebarContent"] [data-baseweb="select"] > div {{
            background: rgba(255,255,255,0.12) !important;
            border: 1.5px solid rgba(255,255,255,0.25) !important;
            color: #FFFFFF !important;
            border-radius: 8px !important;
        }}
        div[data-testid="stSidebarContent"] [data-baseweb="select"] * {{
            color: #FFFFFF !important;
        }}
        div[data-testid="stSidebarContent"] button {{
            background: rgba(255,255,255,0.10) !important;
            border: 1px solid rgba(255,255,255,0.25) !important;
            color: #FFFFFF !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            transition: all 0.2s ease !important;
        }}
        div[data-testid="stSidebarContent"] button:hover {{
            background: rgba(245,166,35,0.25) !important;
            border-color: {BRAND['gold']} !important;
        }}
        div[data-testid="stSidebarContent"] [data-testid="stMetricValue"] div,
        div[data-testid="stSidebarContent"] [data-testid="stMetricValue"] {{
            color: {BRAND['gold']} !important;
            font-size: 1.5rem !important;
            font-weight: 700 !important;
        }}
        div[data-testid="stSidebarContent"] [data-testid="metric-container"] label {{
            color: rgba(255,255,255,0.65) !important;
            font-size: 0.72rem !important;
            font-weight: 600 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.08em !important;
        }}
        div[data-testid="stSidebarContent"] [data-testid="stMetricDelta"] {{
            color: rgba(255,255,255,0.55) !important;
            font-size: 0.78rem !important;
        }}

        /* ── Metric KPI Cards ─────────────────────────────────────── */
        [data-testid="metric-container"] {{
            background: {BRAND['card']} !important;
            border: 1px solid {BRAND['border']} !important;
            border-radius: 12px !important;
            padding: 1.25rem 1.5rem !important;
            box-shadow: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04) !important;
            position: relative !important;
            overflow: hidden !important;
            transition: box-shadow 0.2s ease !important;
        }}
        [data-testid="metric-container"]::before {{
            content: '';
            position: absolute;
            top: 0; left: 0;
            width: 100%; height: 3px;
            background: linear-gradient(90deg, {BRAND['navy']} 0%, {BRAND['gold']} 100%);
        }}
        [data-testid="metric-container"]:hover {{
            box-shadow: 0 4px 12px rgba(0,45,98,0.12) !important;
        }}
        [data-testid="metric-container"] label,
        [data-testid="metric-container"] > div > div:first-child {{
            color: {BRAND['text_secondary']} !important;
            font-size: 0.72rem !important;
            font-weight: 600 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.08em !important;
        }}
        [data-testid="metric-container"] [data-testid="stMetricValue"] > div,
        [data-testid="metric-container"] [data-testid="stMetricValue"] {{
            color: {BRAND['text_primary']} !important;
            font-size: 2rem !important;
            font-weight: 700 !important;
        }}
        [data-testid="metric-container"] [data-testid="stMetricDelta"] {{
            font-size: 0.82rem !important;
            font-weight: 500 !important;
        }}

        /* ── Tabs ─────────────────────────────────────────────────── */
        .stTabs [data-baseweb="tab-list"] {{
            background: {BRAND['card']};
            border: 1px solid {BRAND['border']};
            border-radius: 10px;
            padding: 4px;
            gap: 4px;
        }}
        .stTabs [data-baseweb="tab"] {{
            background: transparent;
            color: {BRAND['text_secondary']};
            font-weight: 600;
            font-size: 0.875rem;
            border-radius: 7px;
            padding: 0.5rem 1.25rem;
            border: none;
            letter-spacing: 0.01em;
        }}
        .stTabs [aria-selected="true"] {{
            background: {BRAND['navy']} !important;
            color: {BRAND['white']} !important;
            box-shadow: 0 1px 4px rgba(0,45,98,0.3) !important;
        }}
        .stTabs [data-baseweb="tab-panel"] {{
            padding-top: 1.5rem;
        }}

        /* ── Buttons ──────────────────────────────────────────────── */
        .stButton > button {{
            background: {BRAND['navy']} !important;
            color: {BRAND['white']} !important;
            border: none !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            font-size: 0.875rem !important;
            padding: 0.5rem 1.25rem !important;
            transition: all 0.2s ease !important;
            letter-spacing: 0.01em !important;
        }}
        .stButton > button:hover {{
            background: {BRAND['navy_mid']} !important;
            box-shadow: 0 4px 12px rgba(0,45,98,0.3) !important;
            transform: translateY(-1px) !important;
        }}

        /* ── Download Button ──────────────────────────────────────── */
        .stDownloadButton > button {{
            background: transparent !important;
            color: {BRAND['navy']} !important;
            border: 1.5px solid {BRAND['navy']} !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
        }}

        /* ── Plotly chart containers ──────────────────────────────── */
        .js-plotly-plot, .plot-container {{
            border-radius: 12px !important;
        }}

        /* ── DataFrames ───────────────────────────────────────────── */
        .stDataFrame {{
            border: 1px solid {BRAND['border']} !important;
            border-radius: 10px !important;
        }}

        /* ── Expanders ────────────────────────────────────────────── */
        .streamlit-expanderHeader {{
            background: {BRAND['card']} !important;
            border: 1px solid {BRAND['border']} !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            color: {BRAND['text_primary']} !important;
        }}
        .streamlit-expanderContent {{
            background: {BRAND['card']} !important;
            border: 1px solid {BRAND['border']} !important;
            border-top: none !important;
            border-radius: 0 0 8px 8px !important;
        }}

        /* ── Main Content Inputs & Textareas ──────────────────────── */
        .main div[data-testid="stTextInput"] div[data-baseweb="input"],
        .main div[data-testid="stTextArea"] div[data-baseweb="textarea"],
        .main div[data-testid="stNumberInput"] div[data-baseweb="input"],
        .main div[data-baseweb="input"],
        .main div[data-baseweb="base-input"] {{
            background-color: #FFFFFF !important;
            border: 1.5px solid #CBD5E1 !important;
            border-radius: 8px !important;
            box-shadow: 0 1px 2px rgba(0,0,0,0.03) !important;
        }}
        .main div[data-testid="stTextInput"] div[data-baseweb="input"]:focus-within,
        .main div[data-testid="stTextArea"] div[data-baseweb="textarea"]:focus-within,
        .main div[data-baseweb="input"]:focus-within {{
            border-color: {BRAND['navy']} !important;
            box-shadow: 0 0 0 3px rgba(0,45,98,0.12) !important;
        }}
        .main div[data-testid="stTextInput"] input,
        .main div[data-testid="stTextArea"] textarea,
        .main div[data-testid="stNumberInput"] input,
        .main div[data-baseweb="input"] input,
        .main div[data-baseweb="base-input"] input,
        .main input[type="text"],
        .main input[type="password"],
        .main input[type="number"],
        .main textarea {{
            color: #0F172A !important;
            -webkit-text-fill-color: #0F172A !important;
            background-color: transparent !important;
            font-size: 0.92rem !important;
            font-weight: 500 !important;
            caret-color: {BRAND['navy']} !important;
        }}
        .main div[data-testid="stTextInput"] input::placeholder,
        .main div[data-testid="stTextArea"] textarea::placeholder,
        .main div[data-baseweb="input"] input::placeholder {{
            color: #94A3B8 !important;
            -webkit-text-fill-color: #94A3B8 !important;
        }}
        .main div[data-baseweb="select"] > div {{
            background-color: #FFFFFF !important;
            border: 1.5px solid #CBD5E1 !important;
            border-radius: 8px !important;
            color: #0F172A !important;
        }}
        .main div[data-baseweb="select"] span {{
            color: #0F172A !important;
        }}

        /* ── Selectbox, Slider labels ─────────────────────────────── */
        .stSelectbox label, .stSlider label, .stTextInput label,
        .stDateInput label, .stNumberInput label, .stRadio label {{
            color: {BRAND['text_primary']} !important;
            font-weight: 600 !important;
            font-size: 0.82rem !important;
            text-transform: uppercase !important;
            letter-spacing: 0.06em !important;
        }}

        /* ── Info / warning / success / error boxes ───────────────── */
        .stAlert {{
            border-radius: 10px !important;
        }}

        /* ── Dividers ─────────────────────────────────────────────── */
        hr {{
            border-color: {BRAND['border']} !important;
            margin: 1.5rem 0 !important;
        }}

        /* ── Custom class: section header ─────────────────────────── */
        .section-header {{
            font-size: 1rem;
            font-weight: 700;
            color: {BRAND['text_secondary']};
            text-transform: uppercase;
            letter-spacing: 0.1em;
            margin: 1.5rem 0 0.75rem 0;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .section-header::after {{
            content: '';
            flex: 1;
            height: 1px;
            background: {BRAND['border']};
        }}

        /* ── Custom class: source badge pill ──────────────────────── */
        .source-badge {{
            display: inline-flex;
            align-items: center;
            gap: 5px;
            padding: 3px 10px;
            border-radius: 20px;
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.04em;
            white-space: nowrap;
        }}

        /* ── Custom class: sentiment pill ─────────────────────────── */
        .sentiment-pill {{
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 2px 10px;
            border-radius: 20px;
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.04em;
        }}

        /* ── Custom class: review card ────────────────────────────── */
        .review-card {{
            background: {BRAND['card']};
            border: 1px solid {BRAND['border']};
            border-radius: 12px;
            padding: 1.25rem 1.5rem;
            margin-bottom: 1rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            transition: box-shadow 0.2s ease;
        }}
        .review-card:hover {{
            box-shadow: 0 4px 16px rgba(0,45,98,0.08);
        }}
        .review-card-header {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 0.75rem;
            flex-wrap: wrap;
        }}
        .review-card-meta {{
            display: flex;
            align-items: center;
            gap: 16px;
            margin-top: 0.75rem;
            padding-top: 0.75rem;
            border-top: 1px solid {BRAND['border']};
            flex-wrap: wrap;
        }}
        .review-card-meta-item {{
            display: flex;
            align-items: center;
            gap: 5px;
            font-size: 0.75rem;
            color: {BRAND['text_muted']};
            font-weight: 500;
        }}
        .review-body {{
            font-size: 0.875rem;
            line-height: 1.6;
            color: {BRAND['text_primary']};
        }}
        .review-author {{
            font-size: 0.82rem;
            font-weight: 600;
            color: {BRAND['text_primary']};
        }}

        /* ── Custom class: data-sync indicator ────────────────────── */
        .sync-badge {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.05em;
        }}
        .sync-live {{
            background: {BRAND['positive_bg']};
            color: {BRAND['positive']};
            border: 1px solid #A7F3D0;
        }}
        .sync-csv {{
            background: {BRAND['neutral_bg']};
            color: {BRAND['neutral']};
            border: 1px solid {BRAND['border_mid']};
        }}
        .pulse-dot {{
            width: 7px; height: 7px;
            border-radius: 50%;
            background: {BRAND['positive']};
            animation: pulse 2s infinite;
            display: inline-block;
        }}
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; transform: scale(1); }}
            50%  {{ opacity: 0.5; transform: scale(1.3); }}
        }}

        /* ── Custom class: channel matrix card ────────────────────── */
        .channel-card {{
            background: {BRAND['card']};
            border: 1px solid {BRAND['border']};
            border-radius: 12px;
            padding: 1.25rem;
            text-align: center;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }}
        .channel-card-icon {{
            font-size: 1.5rem;
            margin-bottom: 0.5rem;
        }}
        .channel-card-label {{
            font-size: 0.72rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: {BRAND['text_secondary']};
            margin-bottom: 0.5rem;
        }}
        .channel-card-value {{
            font-size: 1.75rem;
            font-weight: 800;
            color: {BRAND['text_primary']};
            line-height: 1.1;
        }}
        .channel-card-sub {{
            font-size: 0.75rem;
            color: {BRAND['text_muted']};
            margin-top: 0.25rem;
        }}

        /* ── Platform filter buttons ──────────────────────────────── */
        .platform-filter-btn {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 0.78rem;
            font-weight: 600;
            cursor: pointer;
            border: 1.5px solid {BRAND['border_mid']};
            background: {BRAND['card']};
            color: {BRAND['text_secondary']};
            transition: all 0.15s ease;
        }}
        .platform-filter-btn.active {{
            background: {BRAND['navy']};
            color: white;
            border-color: {BRAND['navy']};
        }}

        /* ── Urgency alert banner ─────────────────────────────────── */
        .urgency-alert {{
            background: {BRAND['negative_bg']};
            border: 1px solid #FECACA;
            border-left: 4px solid {BRAND['negative']};
            border-radius: 8px;
            padding: 0.75rem 1rem;
            margin-bottom: 0.5rem;
            display: flex;
            align-items: flex-start;
            gap: 10px;
        }}
        .urgency-alert-icon {{
            color: {BRAND['negative']};
            font-size: 0.9rem;
            margin-top: 2px;
            flex-shrink: 0;
        }}
        .urgency-alert-text {{
            font-size: 0.82rem;
            color: #991B1B;
            line-height: 1.4;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


inject_global_css()


# =============================================================================
# DATA LOADING  —  Live DB → CSV fallback
# =============================================================================
_DB_TO_LEGACY = {
    "review_id":       "reviewId",
    "user_name":       "userName",
    "user_image_url":  "userImage",
    "content":         "content",
    "rating":          "score",
    "thumbs_up_count": "thumbsUpCount",
    "app_version":     "appVersion",
    "created_at":      "at",
    "reply_content":   "replyContent",
    "replied_at":      "repliedAt",
    "processed_text":  "processed_text",
    "dominant_topic":  "dominant_topic",
    "topic":           "Topic_Label",
    "sentiment":       "ai_sentiment",
    "ai_confidence":   "ai_confidence",
    "ai_compound":     "ai_compound",
    "sentiment_score": "sentiment_score",
}

_LIVE_QUERY = """
SELECT
    review_id, user_name, user_image_url, content, rating,
    thumbs_up_count, app_version, created_at, reply_content, replied_at,
    processed_text, dominant_topic, topic, sentiment,
    ai_confidence, ai_compound, sentiment_score, source, channel_type, aspect
FROM reviews
ORDER BY created_at DESC
LIMIT 150000;
"""


def _postprocess(df: pd.DataFrame) -> pd.DataFrame:
    rename = {k: v for k, v in _DB_TO_LEGACY.items() if k in df.columns}
    df = df.rename(columns=rename)

    # source column — keep raw if present, else tag as csv
    if "source" not in df.columns:
        df["source"] = "csv"

    date_col = "at" if "at" in df.columns else None
    if date_col and date_col in df.columns:
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce", utc=True)
        df[date_col] = df[date_col].dt.tz_localize(None)
        df["month_year"] = df[date_col].dt.to_period("M").astype(str)
        df["year"]       = df[date_col].dt.year
        df["month"]      = df[date_col].dt.month

    if "Topic_Label" not in df.columns and "dominant_topic" in df.columns:
        df["Topic_Label"] = "Topic " + (df["dominant_topic"].fillna(0).astype(int) + 1).astype(str)

    if "ai_sentiment" not in df.columns and "sentiment" in df.columns:
        df["ai_sentiment"] = df["sentiment"]
    if "ai_sentiment" not in df.columns:
        df["ai_sentiment"] = "Neutral"

    if "hybrid_sentiment" not in df.columns:
        df["hybrid_sentiment"] = df.get("ai_sentiment", "Neutral")

    return df


@st.cache_data(ttl=120)
def _db_load() -> pd.DataFrame | None:
    """Load live data from Supabase PostgreSQL via direct driver or st.connection."""
    # 1. Try direct connection (psycopg2 / psycopg)
    try:
        try:
            import psycopg2 as pg_driver
        except ImportError:
            import psycopg as pg_driver

        sec_pg = st.secrets.get("connections", {}).get("postgresql", {})
        db_url = st.secrets.get("SUPABASE_DB_URL") or sec_pg.get("SUPABASE_DB_URL")

        if db_url:
            conn = pg_driver.connect(db_url)
        else:
            conn = pg_driver.connect(
                host=sec_pg.get("host"),
                port=int(sec_pg.get("port", 6543)),
                dbname=sec_pg.get("database", "postgres"),
                user=sec_pg.get("username", "postgres"),
                password=sec_pg.get("password"),
            )

        with conn.cursor() as cur:
            cur.execute(_LIVE_QUERY)
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall()
        conn.close()

        if rows:
            raw_df = pd.DataFrame(rows, columns=cols)
            return _postprocess(raw_df)
    except Exception as exc1:
        # 2. Secondary fallback: Streamlit connection
        try:
            conn_st = st.connection("postgresql", type="sql")
            df_st = conn_st.query(_LIVE_QUERY, ttl=0)
            if df_st is not None and not df_st.empty:
                return _postprocess(df_st)
        except Exception:
            return None
    return None


@st.cache_data(ttl=3600)
def _csv_load() -> pd.DataFrame | None:
    for path in [Path("df_final_enriched.csv"), Path(__file__).parent / "df_final_enriched.csv"]:
        if path.exists():
            df = pd.read_csv(str(path))
            return _postprocess(df)
    return None


def load_data(mode: str = "Live Pipeline Data") -> tuple[pd.DataFrame | None, str]:
    """Returns (dataframe, source_label) based on selected dataset mode."""
    if mode == "Live Pipeline Data":
        df = _db_load()
        if df is not None and not df.empty:
            return df, "live"
        df = _csv_load()
        return df, "csv"
    else:
        df = _csv_load()
        return df, "csv"


@st.cache_data(ttl=3600)
def load_topic_keywords() -> dict:
    defaults = {
        "1": ["login", "app", "open", "otp", "verification"],
        "2": ["payment", "transaction", "money", "account", "bank"],
        "3": ["update", "version", "new", "work", "earlier"],
        "4": ["reward", "point", "redeem", "offer", "discount"],
    }
    for path in [Path("topic_keywords.json"), Path(__file__).parent / "topic_keywords.json"]:
        if path.exists():
            try:
                with open(path) as f:
                    data = json.load(f)
                return data.get("negative_topics", defaults)
            except Exception:
                pass
    return defaults


@st.cache_data(ttl=3600)
def load_competitive() -> pd.DataFrame | None:
    for path in ["competitive_reviews_raw.csv"]:
        if Path(path).exists():
            df = pd.read_csv(path)
            df["at"] = pd.to_datetime(df["at"], errors="coerce")
            return df
    return None


@st.cache_data(ttl=3600)
def load_aspect_csv() -> pd.DataFrame | None:
    for path in ["HelloBPCL_Detailed_Analysis.csv"]:
        if Path(path).exists():
            df = pd.read_csv(path)
            if "Date" in df.columns:
                df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
            return df
    return None


# =============================================================================
# UTILITY HELPERS
# =============================================================================
def stop_words() -> set:
    return {
        "the","a","an","is","it","to","and","of","for","in","on","with",
        "this","that","app","i","my","me","not","very","good","bad","nice",
        "like","just","now","would","could","get","go","want","see","use",
        "so","do","was","are","been","has","have","had","but","or","if","at",
    }


def top_keywords(texts: list, n: int = 10) -> list[tuple]:
    sw = stop_words()
    words = []
    for t in texts:
        if pd.notna(t):
            words.extend(w for w in re.findall(r"\b[a-z]{3,}\b", str(t).lower()) if w not in sw)
    return Counter(words).most_common(n)


def star_html(rating: float | int | None, gold: str = BRAND["gold"]) -> str:
    if rating is None or (isinstance(rating, float) and np.isnan(rating)):
        return "<span style='color:#94A3B8;font-size:0.75rem'>N/A</span>"
    r = max(0, min(5, int(round(float(rating)))))
    filled  = f'<i class="fa-solid fa-star" style="color:{gold};font-size:0.75rem"></i>'
    empty   = f'<i class="fa-regular fa-star" style="color:#E2E8F0;font-size:0.75rem"></i>'
    return "".join([filled] * r + [empty] * (5 - r))


def source_badge_html(source: str) -> str:
    cfg = SOURCE_CONFIG.get(source, SOURCE_CONFIG["csv"])
    color = cfg["color"]
    icon  = cfg["icon"]
    label = cfg["label"]
    # Dark text on light backgrounds for readability
    text_color = "#FFFFFF" if source not in ("app_store",) else "#FFFFFF"
    return (
        f'<span class="source-badge" '
        f'style="background:{color};color:{text_color}">'
        f'<i class="{icon}"></i> {label}</span>'
    )


def sentiment_pill_html(sentiment: str, score: float | None = None) -> str:
    cfg = {
        "Positive": (BRAND["positive"],    BRAND["positive_bg"], "#A7F3D0", "fa-solid fa-arrow-trend-up"),
        "Negative": (BRAND["negative"],    BRAND["negative_bg"], "#FECACA", "fa-solid fa-arrow-trend-down"),
        "Neutral":  (BRAND["neutral"],     BRAND["neutral_bg"],  BRAND["border_mid"], "fa-solid fa-minus"),
    }.get(sentiment, (BRAND["neutral"], BRAND["neutral_bg"], BRAND["border_mid"], "fa-solid fa-minus"))
    color, bg, border, icon = cfg
    score_str = f" {score:+.2f}" if score is not None else ""
    return (
        f'<span class="sentiment-pill" '
        f'style="background:{bg};color:{color};border:1px solid {border}">'
        f'<i class="{icon}"></i> {sentiment}{score_str}</span>'
    )


def apply_filters(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    fd = df.copy()
    if filters.get("source") and filters["source"] != "All":
        fd = fd[fd["source"] == filters["source"]]
    if filters.get("sentiment") and filters["sentiment"] != "All":
        fd = fd[fd["ai_sentiment"] == filters["sentiment"]]
    if filters.get("topic") and filters["topic"] != "All" and "Topic_Label" in fd.columns:
        fd = fd[fd["Topic_Label"] == filters["topic"]]
    if filters.get("rating_range") and "score" in fd.columns:
        lo, hi = filters["rating_range"]
        fd = fd[(fd["score"] >= lo) & (fd["score"] <= hi)]
    if filters.get("date_range") and "at" in fd.columns:
        lo, hi = filters["date_range"]
        fd = fd[(fd["at"].dt.date >= lo) & (fd["at"].dt.date <= hi)]
    if filters.get("search") and "content" in fd.columns:
        q = filters["search"].lower()
        fd = fd[fd["content"].str.lower().str.contains(q, na=False)]
    return fd


def nss(df: pd.DataFrame) -> float:
    if df.empty or "ai_sentiment" not in df.columns:
        return 0.0
    total = len(df)
    pos   = (df["ai_sentiment"] == "Positive").sum()
    neg   = (df["ai_sentiment"] == "Negative").sum()
    return round((pos - neg) / total * 100, 1) if total > 0 else 0.0


def pct(df: pd.DataFrame, label: str) -> float:
    if df.empty or "ai_sentiment" not in df.columns:
        return 0.0
    return round((df["ai_sentiment"] == label).sum() / len(df) * 100, 1)


# =============================================================================
# PLOTLY CHART BUILDERS  — shared style
# =============================================================================
_CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor =BRAND["plot_bg"],
    font=dict(family="Inter, system-ui, sans-serif", color=BRAND["text_primary"]),
    hoverlabel=dict(
        bgcolor=BRAND["navy"],
        font_color=BRAND["white"],
        font_size=12,
        bordercolor=BRAND["navy"],
    ),
)


def _axes_style(**overrides) -> dict:
    base = dict(
        gridcolor=BRAND["grid"],
        gridwidth=1,
        linecolor=BRAND["border"],
        tickfont=dict(color=BRAND["text_secondary"], size=11),
        title_font=dict(color=BRAND["text_secondary"], size=12),
        zeroline=False,
    )
    base.update(overrides)
    return base


def chart_sentiment_donut(df: pd.DataFrame) -> go.Figure:
    counts = df["ai_sentiment"].value_counts().reindex(["Positive", "Neutral", "Negative"], fill_value=0)
    _nss   = nss(df)
    colors = [BRAND["positive"], BRAND["neutral"], BRAND["negative"]]

    fig = go.Figure(go.Pie(
        labels=counts.index,
        values=counts.values,
        hole=0.62,
        marker=dict(colors=colors, line=dict(color=BRAND["white"], width=2)),
        textinfo="percent",
        textfont=dict(size=12, color=BRAND["white"]),
        hovertemplate="<b>%{label}</b><br>%{value:,} reviews<br>%{percent}<extra></extra>",
        direction="clockwise",
        sort=False,
    ))

    fig.add_annotation(
        text=f"<b>{_nss:+.1f}</b><br><span style='font-size:9px'>NSS</span>",
        x=0.5, y=0.5,
        font=dict(size=22, color=BRAND["navy"], family="Inter, sans-serif"),
        showarrow=False,
        align="center",
    )

    fig.update_layout(
        **_CHART_LAYOUT,
        title=dict(text="Sentiment Distribution", font=dict(size=14, color=BRAND["text_primary"]), x=0.5, xanchor="center"),
        showlegend=True,
        legend=dict(
            orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5,
            font=dict(size=11), bgcolor="rgba(0,0,0,0)",
        ),
        height=300,
        margin=dict(l=0, r=0, t=50, b=20),
    )
    return fig


def chart_aspect_stacked_bar(df: pd.DataFrame) -> go.Figure | None:
    col = "aspect" if "aspect" in df.columns else ("Topic_Label" if "Topic_Label" in df.columns else None)
    if col is None or df.empty:
        return None

    top = df[col].value_counts().head(10).index.tolist()
    sub = df[df[col].isin(top)]
    if sub.empty:
        return None

    pivot = (
        sub.groupby([col, "ai_sentiment"]).size()
        .unstack(fill_value=0)
        .reindex(columns=["Positive", "Neutral", "Negative"], fill_value=0)
    )
    pivot_pct = pivot.div(pivot.sum(axis=1), axis=0) * 100
    # Sort by negative pct descending (most critical first)
    pivot_pct = pivot_pct.sort_values("Negative", ascending=True)

    fig = go.Figure()
    for sentiment, color in [("Positive", BRAND["positive"]), ("Neutral", BRAND["neutral"]), ("Negative", BRAND["negative"])]:
        if sentiment in pivot_pct.columns:
            fig.add_trace(go.Bar(
                name=sentiment,
                y=pivot_pct.index,
                x=pivot_pct[sentiment],
                orientation="h",
                marker_color=color,
                hovertemplate=f"<b>%{{y}}</b><br>{sentiment}: %{{x:.1f}}%<extra></extra>",
                text=pivot_pct[sentiment].apply(lambda v: f"{v:.0f}%" if v >= 8 else ""),
                textfont=dict(size=10, color=BRAND["white"]),
                textposition="inside",
            ))

    fig.update_layout(
        **_CHART_LAYOUT,
        barmode="stack",
        title=dict(text="Aspect Sentiment Breakdown", font=dict(size=14, color=BRAND["text_primary"]), x=0, xanchor="left"),
        xaxis=_axes_style( title="Percentage", ticksuffix="%", range=[0, 100]),
        yaxis=_axes_style( title=""),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    font=dict(size=11), bgcolor="rgba(0,0,0,0)"),
        height=360,
        margin=dict(l=0, r=0, t=50, b=0),
    )
    return fig


def chart_timeline(df: pd.DataFrame) -> go.Figure | None:
    if "at" not in df.columns or df.empty:
        return None

    agg = (
        df.assign(week=df["at"].dt.to_period("W").dt.start_time)
        .groupby(["week", "ai_sentiment"])
        .size()
        .reset_index(name="count")
    )
    if agg.empty:
        return None

    fig = go.Figure()
    for sentiment, color in [("Positive", BRAND["positive"]), ("Neutral", BRAND["neutral"]), ("Negative", BRAND["negative"])]:
        sub = agg[agg["ai_sentiment"] == sentiment].sort_values("week")
        if sub.empty:
            continue
        fig.add_trace(go.Scatter(
            x=sub["week"], y=sub["count"],
            name=sentiment, mode="lines",
            line=dict(color=color, width=2.5, shape="spline", smoothing=0.8),
            fill="tozeroy",
            fillcolor=color.replace(")", ",0.07)").replace("rgb", "rgba") if "rgb" in color else color + "12",
            hovertemplate=f"<b>{sentiment}</b><br>%{{x|%b %Y}}: %{{y:,}} reviews<extra></extra>",
        ))

    fig.update_layout(
        **_CHART_LAYOUT,
        title=dict(text="Omnichannel Volume & Sentiment Timeline", font=dict(size=14, color=BRAND["text_primary"]), x=0, xanchor="left"),
        xaxis=_axes_style( title=""),
        yaxis=_axes_style( title="Weekly Reviews"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    font=dict(size=11), bgcolor="rgba(0,0,0,0)"),
        height=300,
        hovermode="x unified",
        margin=dict(l=0, r=0, t=50, b=0),
    )
    return fig


def chart_complaint_heatmap(df: pd.DataFrame) -> go.Figure | None:
    col = "aspect" if "aspect" in df.columns else ("Topic_Label" if "Topic_Label" in df.columns else None)
    if col is None or "ai_sentiment" not in df.columns or df.empty:
        return None

    top_aspects = df[col].value_counts().head(8).index.tolist()
    top_sources = df["source"].value_counts().head(6).index.tolist()

    sub = df[df[col].isin(top_aspects) & df["source"].isin(top_sources)]
    if sub.empty:
        return None

    neg = sub[sub["ai_sentiment"] == "Negative"]
    pivot = (
        neg.groupby(["source", col]).size()
        .unstack(fill_value=0)
        .reindex(columns=top_aspects, fill_value=0)
        .reindex(index=top_sources, fill_value=0)
    )

    # Rename source index to human-readable labels
    pivot.index = [SOURCE_CONFIG.get(s, {}).get("label", s) for s in pivot.index]

    fig = px.imshow(
        pivot.values,
        x=[str(c) for c in pivot.columns],
        y=[str(r) for r in pivot.index],
        color_continuous_scale=[[0, "#FFF5F5"], [0.5, "#FCA5A5"], [1, BRAND["negative"]]],
        text_auto=True,
        aspect="auto",
    )
    fig.update_traces(
        textfont=dict(size=11, color=BRAND["text_primary"]),
        hovertemplate="<b>%{y}</b> × <b>%{x}</b><br>Negative reviews: %{z}<extra></extra>",
    )
    fig.update_layout(
        **_CHART_LAYOUT,
        title=dict(text="Complaint Density Matrix (Negative Reviews)", font=dict(size=14, color=BRAND["text_primary"]), x=0, xanchor="left"),
        xaxis=_axes_style( title=""),
        yaxis=_axes_style( title=""),
        coloraxis_showscale=False,
        height=300,
        margin=dict(l=0, r=0, t=50, b=0),
    )
    return fig


def chart_rating_bar(df: pd.DataFrame) -> go.Figure | None:
    if "score" not in df.columns or df.empty:
        return None
    counts = df["score"].value_counts().sort_index()
    total  = counts.sum()
    colors = {1: BRAND["negative"], 2: "#F97316", 3: BRAND["neutral"], 4: "#84CC16", 5: BRAND["positive"]}

    fig = go.Figure()
    for star, cnt in counts.items():
        fig.add_trace(go.Bar(
            x=[star], y=[cnt],
            name=f"{int(star)} star",
            marker_color=colors.get(int(star), BRAND["neutral"]),
            text=[f"{cnt/total*100:.1f}%"],
            textposition="outside",
            textfont=dict(size=11, color=BRAND["text_secondary"]),
            hovertemplate=f"<b>{int(star)} Stars</b><br>%{{y:,}} reviews (%{{text}})<extra></extra>",
            showlegend=False,
        ))

    fig.update_layout(
        **_CHART_LAYOUT,
        title=dict(text="Star Rating Distribution", font=dict(size=14, color=BRAND["text_primary"]), x=0, xanchor="left"),
        xaxis=_axes_style( title="Star Rating", tickmode="linear", tick0=1, dtick=1),
        yaxis=_axes_style( title="Reviews"),
        barmode="group",
        height=280,
        bargap=0.35,
        margin=dict(l=0, r=0, t=50, b=0),
    )
    return fig


def chart_topic_trend(df: pd.DataFrame) -> go.Figure | None:
    if "Topic_Label" not in df.columns or "at" not in df.columns or df.empty:
        return None

    agg = (
        df.assign(month=df["at"].dt.to_period("M").dt.start_time)
        .groupby(["month", "Topic_Label"])
        .size()
        .reset_index(name="count")
        .sort_values("month")
    )
    if agg.empty:
        return None

    top_topics = df["Topic_Label"].value_counts().head(5).index.tolist()
    agg = agg[agg["Topic_Label"].isin(top_topics)]

    fig = px.line(
        agg, x="month", y="count", color="Topic_Label",
        markers=True,
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig.update_traces(line=dict(width=2), marker=dict(size=5))
    fig.update_layout(
        **_CHART_LAYOUT,
        title=dict(text="Temporal Topic Evolution (Top 5)", font=dict(size=14, color=BRAND["text_primary"]), x=0, xanchor="left"),
        xaxis=_axes_style( title=""),
        yaxis=_axes_style( title="Reviews"),
        legend=dict(title="", orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    font=dict(size=10), bgcolor="rgba(0,0,0,0)"),
        height=300,
        margin=dict(l=0, r=0, t=50, b=0),
    )
    return fig


def chart_keyword_comparison(df: pd.DataFrame) -> go.Figure | None:
    if "ai_sentiment" not in df.columns or "content" not in df.columns or df.empty:
        return None

    neg_kw = top_keywords(df[df["ai_sentiment"] == "Negative"]["content"].tolist(), 10)
    pos_kw = top_keywords(df[df["ai_sentiment"] == "Positive"]["content"].tolist(), 10)

    if not neg_kw or not pos_kw:
        return None

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=["Critical Keywords (Negative)", "Praise Keywords (Positive)"],
        horizontal_spacing=0.08,
    )
    nw, nc = zip(*neg_kw)
    pw, pc = zip(*pos_kw)
    fig.add_trace(go.Bar(x=list(nc), y=list(nw), orientation="h", marker_color=BRAND["negative"],
                         hovertemplate="<b>%{y}</b>: %{x:,}<extra></extra>", name=""), row=1, col=1)
    fig.add_trace(go.Bar(x=list(pc), y=list(pw), orientation="h", marker_color=BRAND["positive"],
                         hovertemplate="<b>%{y}</b>: %{x:,}<extra></extra>", name=""), row=1, col=2)

    fig.update_layout(
        **_CHART_LAYOUT,
        title=dict(text="Keyword Signal Comparison", font=dict(size=14, color=BRAND["text_primary"]), x=0, xanchor="left"),
        showlegend=False,
        height=320,
        margin=dict(l=0, r=0, t=50, b=0),
    )
    for ax in ["xaxis", "xaxis2"]:
        fig.update_layout(**{ax: _axes_style()})
    for ax in ["yaxis", "yaxis2"]:
        fig.update_layout(**{ax: _axes_style()})
    return fig


def chart_violin(df: pd.DataFrame) -> go.Figure | None:
    if "score" not in df.columns or "ai_sentiment" not in df.columns or df.empty:
        return None

    fig = go.Figure()
    for sentiment, color in [("Positive", BRAND["positive"]), ("Neutral", BRAND["neutral"]), ("Negative", BRAND["negative"])]:
        sub = df[df["ai_sentiment"] == sentiment]["score"].dropna()
        if sub.empty:
            continue
        fig.add_trace(go.Violin(
            x=[sentiment] * len(sub), y=sub,
            name=sentiment, fillcolor=color, line_color=color,
            opacity=0.75, box_visible=True, meanline_visible=True,
            points="outliers",
            hovertemplate=f"<b>{sentiment}</b><br>Rating: %{{y}}<extra></extra>",
        ))

    fig.update_layout(
        **_CHART_LAYOUT,
        title=dict(text="Rating Distribution by Sentiment", font=dict(size=14, color=BRAND["text_primary"]), x=0, xanchor="left"),
        xaxis=_axes_style( title=""),
        yaxis=_axes_style( title="Star Rating"),
        height=320,
        showlegend=False,
        margin=dict(l=0, r=0, t=50, b=0),
    )
    return fig


def chart_gauge(value: float, title: str = "Sentiment Health") -> go.Figure:
    normalized = (value + 1) * 50
    if normalized >= 66:
        bar_color = BRAND["positive"]
    elif normalized <= 33:
        bar_color = BRAND["negative"]
    else:
        bar_color = BRAND["gold"]

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=normalized,
        domain={"x": [0, 1], "y": [0, 1]},
        title={"text": title, "font": {"size": 14, "color": BRAND["text_primary"]}},
        number={"font": {"size": 36, "color": BRAND["navy"]}, "suffix": "%"},
        gauge={
            "axis": {"range": [0, 100], "tickfont": {"size": 10, "color": BRAND["text_muted"]}},
            "bar":  {"color": bar_color, "thickness": 0.75},
            "bgcolor": "#F8FAFC",
            "borderwidth": 0,
            "steps": [
                {"range": [0, 33],  "color": "#FEE2E2"},
                {"range": [33, 66], "color": "#FEF9EE"},
                {"range": [66, 100],"color": "#D1FAE5"},
            ],
        },
    ))
    fig.update_layout(
        height=240,
        margin=dict(l=20, r=20, t=50, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif"),
    )
    return fig


# =============================================================================
# REVIEW CARD RENDERER
# =============================================================================
def render_review_cards(df: pd.DataFrame, max_cards: int = 20):
    if df.empty:
        st.info("No reviews match the current filters.")
        return

    for _, row in df.head(max_cards).iterrows():
        source    = str(row.get("source", "csv"))
        sentiment = str(row.get("ai_sentiment", "Neutral"))
        score     = row.get("score") if pd.notna(row.get("score", None)) else None
        content   = str(row.get("content", "")) or "—"
        author    = str(row.get("userName") or row.get("user_name") or "Anonymous")
        date_raw  = row.get("at", None)
        date_str  = str(date_raw)[:10] if date_raw is not None and pd.notna(date_raw) else "—"
        version   = str(row.get("appVersion") or row.get("app_version") or "").strip() or "—"
        topic     = str(row.get("Topic_Label") or row.get("topic") or "General")
        aspect    = str(row.get("aspect") or "").strip() or topic
        s_score   = row.get("sentiment_score") or row.get("ai_compound") or None
        s_score_f = float(s_score) if s_score is not None and pd.notna(s_score) else None
        thumbs    = int(row.get("thumbsUpCount") or row.get("thumbs_up_count") or 0)

        badge   = source_badge_html(source)
        stars   = star_html(score)
        s_pill  = sentiment_pill_html(sentiment, s_score_f)

        # Aspect tag
        aspect_tag = (
            f'<span style="display:inline-flex;align-items:center;gap:4px;'
            f'padding:2px 9px;border-radius:20px;font-size:0.70rem;font-weight:600;'
            f'background:{BRAND["neutral_bg"]};color:{BRAND["neutral"]};'
            f'border:1px solid {BRAND["border_mid"]}">'
            f'<i class="fa-solid fa-tag" style="font-size:0.65rem"></i> {aspect}</span>'
        )

        st.markdown(
            f"""
            <div class="review-card">
              <div class="review-card-header">
                {badge}
                <span style="display:inline-flex;align-items:center;gap:3px">{stars}</span>
                {s_pill}
                {aspect_tag}
              </div>
              <div class="review-body">{content[:400]}{"…" if len(content) > 400 else ""}</div>
              <div class="review-card-meta">
                <div class="review-card-meta-item">
                  <i class="fa-solid fa-user" style="font-size:0.65rem"></i>
                  <span class="review-author">{author}</span>
                </div>
                <div class="review-card-meta-item">
                  <i class="fa-solid fa-calendar" style="font-size:0.65rem"></i>
                  {date_str}
                </div>
                <div class="review-card-meta-item">
                  <i class="fa-solid fa-code-branch" style="font-size:0.65rem"></i>
                  v{version}
                </div>
                <div class="review-card-meta-item">
                  <i class="fa-solid fa-thumbs-up" style="font-size:0.65rem"></i>
                  {thumbs:,}
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# =============================================================================
# SIDEBAR
# =============================================================================
def render_sidebar(df: pd.DataFrame, source_label: str) -> dict:
    """Renders sidebar controls; returns filter dict."""
    with st.sidebar:
        # ── Branding ──────────────────────────────────────────────────────────
        st.markdown(
            f"""
            <div style="padding:1.5rem 0.5rem 1rem;text-align:center">
              <div style="font-size:1.5rem;font-weight:800;color:#FFFFFF;
                          letter-spacing:-0.02em;line-height:1.1">BPCL</div>
              <div style="font-size:0.65rem;font-weight:600;color:rgba(255,255,255,0.55);
                          text-transform:uppercase;letter-spacing:0.14em;margin-top:2px">
                Customer Intelligence
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ── Dataset Selector ──────────────────────────────────────────────────
        db_available = (
            hasattr(st, "secrets")
            and "connections" in st.secrets
            and "postgresql" in st.secrets.get("connections", {})
        )
        dataset_options = ["Live Pipeline Data", "Historical Analysis"] if db_available else ["Historical Analysis"]
        curr_mode = st.session_state.get("dataset_mode", dataset_options[0])
        curr_idx = dataset_options.index(curr_mode) if curr_mode in dataset_options else 0

        def _on_mode_change():
            st.session_state["dataset_mode"] = st.session_state["dataset_selector_key"]

        st.radio(
            "Dataset View",
            options=dataset_options,
            index=curr_idx,
            key="dataset_selector_key",
            on_change=_on_mode_change,
            help="Switch between live multi-source database and historical 100k review benchmark.",
        )

        # ── Data source indicator ──────────────────────────────────────────────
        if source_label == "live":
            st.markdown(
                '<div style="text-align:center;margin-bottom:1rem">'
                '<span class="sync-badge sync-live">'
                f'<span class="pulse-dot"></span> Live Database · {len(df):,} reviews</span></div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div style="text-align:center;margin-bottom:1rem">'
                '<span class="sync-badge sync-csv">'
                '<i class="fa-solid fa-database" style="font-size:0.65rem"></i>'
                f' Historical Benchmark · {len(df):,} reviews</span></div>',
                unsafe_allow_html=True,
            )

        st.divider()

        # ── Refresh ────────────────────────────────────────────────────────────
        if st.button(
            "\u2007 Refresh Data",
            use_container_width=True,
            help="Clear cache and reload from data source",
        ):
            st.cache_data.clear()
            st.rerun()

        st.divider()

        # ── Filters header ─────────────────────────────────────────────────────
        st.markdown(
            '<div style="font-size:0.68rem;font-weight:700;color:rgba(255,255,255,0.5);'
            'text-transform:uppercase;letter-spacing:0.12em;margin-bottom:0.75rem">'
            '<i class="fa-solid fa-sliders"></i>  Intelligence Filters</div>',
            unsafe_allow_html=True,
        )

        # ── Source filter ──────────────────────────────────────────────────────
        available_sources = ["All"] + sorted(df["source"].dropna().unique().tolist()) if "source" in df.columns else ["All"]
        source_labels_map = {s: SOURCE_CONFIG.get(s, {}).get("label", s) for s in available_sources if s != "All"}
        source_display    = ["All"] + [source_labels_map.get(s, s) for s in available_sources[1:]]
        sel_source_idx    = st.selectbox(
            "Platform",
            range(len(source_display)),
            format_func=lambda i: source_display[i],
        )
        sel_source = available_sources[sel_source_idx]

        # ── Sentiment filter ───────────────────────────────────────────────────
        sel_sentiment = st.selectbox("Sentiment", ["All", "Positive", "Neutral", "Negative"])

        # ── Topic filter ───────────────────────────────────────────────────────
        if "Topic_Label" in df.columns:
            topics = ["All"] + sorted(df["Topic_Label"].dropna().unique().tolist())
            sel_topic = st.selectbox("Topic", topics)
        else:
            sel_topic = "All"

        # ── Rating filter ──────────────────────────────────────────────────────
        rating_range = None
        if "score" in df.columns:
            mn = int(df["score"].dropna().min()) if not df["score"].dropna().empty else 1
            mx = int(df["score"].dropna().max()) if not df["score"].dropna().empty else 5
            rating_range = st.slider("Star Rating", mn, mx, (mn, mx))

        # ── Date filter ────────────────────────────────────────────────────────
        date_range = None
        if "at" in df.columns and df["at"].notna().any():
            min_d = df["at"].min().date()
            max_d = df["at"].max().date()
            preset = st.selectbox(
                "Date Range",
                ["All Time", "Last 7 Days", "Last 30 Days", "Last 90 Days", "Last Year", "Custom"],
            )
            today = datetime.now().date()
            if preset == "All Time":
                date_range = (min_d, max_d)
            elif preset == "Last 7 Days":
                date_range = (max_d - timedelta(days=7), max_d)
            elif preset == "Last 30 Days":
                date_range = (max_d - timedelta(days=30), max_d)
            elif preset == "Last 90 Days":
                date_range = (max_d - timedelta(days=90), max_d)
            elif preset == "Last Year":
                date_range = (max_d - timedelta(days=365), max_d)
            else:
                date_range = st.date_input("Pick range", value=(min_d, max_d), min_value=min_d, max_value=max_d)
                if isinstance(date_range, tuple) and len(date_range) == 2:
                    pass
                else:
                    date_range = (min_d, max_d)

        # ── Search ─────────────────────────────────────────────────────────────
        search_q = st.text_input("Keyword Search", placeholder="e.g. OTP, refund, delivery...")

        st.divider()

        # ── Dataset stats ──────────────────────────────────────────────────────
        st.markdown(
            '<div style="font-size:0.68rem;font-weight:700;color:rgba(255,255,255,0.5);'
            'text-transform:uppercase;letter-spacing:0.12em;margin-bottom:0.5rem">'
            'Dataset Overview</div>',
            unsafe_allow_html=True,
        )
        st.metric("Total Reviews", f"{len(df):,}")
        if "source" in df.columns:
            st.metric("Active Channels", df["source"].nunique())
        if "at" in df.columns and df["at"].notna().any():
            st.metric("Latest Entry", str(df["at"].max())[:10])

        st.divider()

        # ── Export ─────────────────────────────────────────────────────────────
        st.markdown(
            '<div style="font-size:0.68rem;font-weight:700;color:rgba(255,255,255,0.5);'
            'text-transform:uppercase;letter-spacing:0.12em;margin-bottom:0.5rem">'
            'Export</div>',
            unsafe_allow_html=True,
        )
        st.download_button(
            label="Download Filtered CSV",
            data="",          # filled after filters applied
            file_name="bpcl_voc_export.csv",
            mime="text/csv",
            use_container_width=True,
            key="sidebar_export_placeholder",
            disabled=True,
        )

    return {
        "source":       sel_source,
        "sentiment":    sel_sentiment,
        "topic":        sel_topic,
        "rating_range": rating_range,
        "date_range":   date_range,
        "search":       search_q,
    }


# =============================================================================
# HEADER + KPI RIBBON
# =============================================================================
def render_header(df_filtered: pd.DataFrame, df_full: pd.DataFrame, source_label: str):
    # ── Enterprise Header ──────────────────────────────────────────────────────
    sync_html = (
        '<span class="sync-badge sync-live" style="font-size:0.65rem">'
        '<span class="pulse-dot"></span>&nbsp;Live Pipeline Active</span>'
        if source_label == "live"
        else
        '<span class="sync-badge sync-csv" style="font-size:0.65rem">'
        '<i class="fa-solid fa-database" style="font-size:0.6rem"></i>&nbsp;Historical Dataset</span>'
    )

    st.markdown(
        f"""
        <div style="display:flex;align-items:center;justify-content:space-between;
                    padding:1.25rem 1.75rem;background:{BRAND['navy']};
                    border-radius:14px;margin-bottom:1.5rem;
                    box-shadow:0 4px 20px rgba(0,45,98,0.2)">
          <div>
            <div style="font-size:1.5rem;font-weight:800;color:#FFFFFF;
                        letter-spacing:-0.02em;margin-bottom:2px">
              BPCL Customer Intelligence Platform
            </div>
            <div style="font-size:0.8rem;color:rgba(255,255,255,0.65);font-weight:400">
              Bharat Petroleum Corporation Limited &nbsp;&bull;&nbsp;
              Voice of Customer Analytics &nbsp;&bull;&nbsp;
              <i class="fa-brands fa-google-play"></i> Google Play &nbsp;
              <i class="fa-brands fa-apple"></i> App Store &nbsp;
              <i class="fa-brands fa-youtube"></i> YouTube &nbsp;
              <i class="fa-solid fa-comments"></i> Consumer Forum
            </div>
          </div>
          <div style="display:flex;flex-direction:column;align-items:flex-end;gap:6px">
            {sync_html}
            <div style="font-size:0.68rem;color:rgba(255,255,255,0.45)">
              <i class="fa-regular fa-clock"></i>&nbsp;
              {datetime.now().strftime("%d %b %Y, %H:%M IST")}
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── KPI Ribbon ─────────────────────────────────────────────────────────────
    total  = len(df_filtered)
    _nss   = nss(df_filtered)
    pos_p  = pct(df_filtered, "Positive")
    neg_p  = pct(df_filtered, "Negative")
    avg_r  = df_filtered["score"].mean() if "score" in df_filtered.columns and not df_filtered["score"].dropna().empty else 0
    csi    = round(avg_r / 5 * 100, 1)

    # Urgency count = reviews with Negative sentiment rated 1 star
    urgency = 0
    if "score" in df_filtered.columns and "ai_sentiment" in df_filtered.columns:
        urgency = int(((df_filtered["ai_sentiment"] == "Negative") & (df_filtered["score"] <= 2)).sum())

    # Delta vs all-time
    total_all = len(df_full)
    nss_color = BRAND["positive"] if _nss >= 0 else BRAND["negative"]
    nss_icon  = "fa-arrow-trend-up" if _nss >= 0 else "fa-arrow-trend-down"

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric(
            label="Total Reviews",
            value=f"{total:,}",
            delta=f"{total_all:,} all-time" if total < total_all else f"{total:,} reviews ingested",
        )
    with k2:
        st.metric(
            label="Customer Satisfaction Index",
            value=f"{csi:.1f}%",
            delta=f"{avg_r:.2f} / 5.0 stars",
        )
    with k3:
        delta_color = "normal" if _nss >= 0 else "inverse"
        st.metric(
            label="Net Sentiment Score (NSS)",
            value=f"{_nss:+.1f}",
            delta=f"{pos_p:.1f}% Positive  /  {neg_p:.1f}% Negative",
            delta_color=delta_color,
        )
    with k4:
        urgency_delta = "critical" if urgency > 50 else "review required"
        st.metric(
            label="High-Urgency Grievances",
            value=f"{urgency:,}",
            delta=f"1-2 star negative reviews",
            delta_color="inverse" if urgency > 0 else "off",
        )


# =============================================================================
# CHANNEL PERFORMANCE MATRIX
# =============================================================================
def render_channel_matrix(df: pd.DataFrame):
    if "source" not in df.columns or df.empty:
        return

    st.markdown('<div class="section-header"><i class="fa-solid fa-network-wired"></i> Channel Performance Matrix</div>', unsafe_allow_html=True)

    sources = df["source"].dropna().unique()
    cols    = st.columns(min(len(sources), 6))

    for i, source in enumerate(sources[:6]):
        sub = df[df["source"] == source]
        cfg = SOURCE_CONFIG.get(source, {"label": source, "color": BRAND["navy"], "icon": "fa-solid fa-database"})
        avg_rating  = sub["score"].mean() if "score" in sub.columns and sub["score"].notna().any() else None
        neg_rate    = pct(sub, "Negative")
        sub_nss     = nss(sub)
        vol         = len(sub)
        rating_str  = f"{avg_rating:.1f} / 5" if avg_rating else "N/A"
        nss_color   = BRAND["positive"] if sub_nss >= 0 else BRAND["negative"]

        with cols[i % len(cols)]:
            st.markdown(
                f"""
                <div class="channel-card">
                  <div class="channel-card-icon">
                    <i class="{cfg['icon']}" style="color:{cfg['color']}"></i>
                  </div>
                  <div class="channel-card-label">{cfg['label']}</div>
                  <div class="channel-card-value">{vol:,}</div>
                  <div class="channel-card-sub">reviews</div>
                  <div style="margin-top:0.75rem;padding-top:0.75rem;
                              border-top:1px solid {BRAND['border']}">
                    <div style="display:flex;justify-content:space-between;
                                font-size:0.72rem;margin-bottom:4px">
                      <span style="color:{BRAND['text_muted']}">Avg Rating</span>
                      <span style="font-weight:600;color:{BRAND['text_primary']}">{rating_str}</span>
                    </div>
                    <div style="display:flex;justify-content:space-between;
                                font-size:0.72rem;margin-bottom:4px">
                      <span style="color:{BRAND['text_muted']}">Neg. Rate</span>
                      <span style="font-weight:600;color:{BRAND['negative']}">{neg_rate:.1f}%</span>
                    </div>
                    <div style="display:flex;justify-content:space-between;font-size:0.72rem">
                      <span style="color:{BRAND['text_muted']}">NSS</span>
                      <span style="font-weight:700;color:{nss_color}">{sub_nss:+.1f}</span>
                    </div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


# =============================================================================
# URGENCY ALERTS
# =============================================================================
def render_urgency_alerts(df: pd.DataFrame, max_alerts: int = 5):
    if df.empty or "ai_sentiment" not in df.columns:
        return

    critical = df[
        (df["ai_sentiment"] == "Negative") &
        (df.get("score", pd.Series(dtype=float)) <= 2 if "score" in df.columns else True)
    ].sort_values("at" if "at" in df.columns else df.columns[0], ascending=False)

    if critical.empty:
        st.markdown(
            f'<div style="padding:0.75rem 1rem;background:{BRAND["positive_bg"]};'
            f'border:1px solid #A7F3D0;border-radius:8px;font-size:0.82rem;'
            f'color:#065F46"><i class="fa-solid fa-circle-check"></i> '
            f'No high-urgency grievances in the current filter window.</div>',
            unsafe_allow_html=True,
        )
        return

    for _, row in critical.head(max_alerts).iterrows():
        source  = str(row.get("source", "csv"))
        content = str(row.get("content", ""))[:160]
        date_s  = str(row.get("at", ""))[:10]
        badge   = source_badge_html(source)
        st.markdown(
            f"""
            <div class="urgency-alert">
              <div class="urgency-alert-icon"><i class="fa-solid fa-triangle-exclamation"></i></div>
              <div class="urgency-alert-text">
                {badge}&nbsp;&nbsp;<strong>{date_s}</strong><br>
                {content}{"…" if len(str(row.get("content",""))>160) else ""}
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# =============================================================================
# PAGE: OVERVIEW  (Tab 1 → Internal Pulse → Overview)
# =============================================================================
def page_overview(df_full: pd.DataFrame, df_filt: pd.DataFrame, source_label: str):
    render_header(df_filt, df_full, source_label)
    render_channel_matrix(df_filt)
    st.markdown("<br>", unsafe_allow_html=True)

    # Row 1: Donut + Gauge + Timeline
    c1, c2, c3 = st.columns([1.1, 1.1, 2.1])
    with c1:
        fig_d = chart_sentiment_donut(df_filt)
        st.plotly_chart(fig_d, use_container_width=True, config={"displayModeBar": False})
    with c2:
        avg_s = df_filt["sentiment_score"].mean() if "sentiment_score" in df_filt.columns and not df_filt["sentiment_score"].dropna().empty else 0
        fig_g = chart_gauge(float(avg_s), "Sentiment Health")
        st.plotly_chart(fig_g, use_container_width=True, config={"displayModeBar": False})
    with c3:
        fig_t = chart_timeline(df_filt)
        if fig_t:
            st.plotly_chart(fig_t, use_container_width=True, config={"displayModeBar": False})

    st.divider()

    # Row 2: Aspect stacked bar + Rating bar
    c4, c5 = st.columns([1.8, 1.2])
    with c4:
        st.markdown('<div class="section-header"><i class="fa-solid fa-layer-group"></i> Aspect Sentiment Breakdown</div>', unsafe_allow_html=True)
        fig_a = chart_aspect_stacked_bar(df_filt)
        if fig_a:
            st.plotly_chart(fig_a, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("Aspect data not available. Run the pipeline to enrich data with aspect labels.")
    with c5:
        st.markdown('<div class="section-header"><i class="fa-solid fa-star"></i> Rating Distribution</div>', unsafe_allow_html=True)
        fig_r = chart_rating_bar(df_filt)
        if fig_r:
            st.plotly_chart(fig_r, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("Rating data not available.")

    st.divider()

    # Row 3: Complaint density heatmap + Urgency panel
    c6, c7 = st.columns([1.8, 1.2])
    with c6:
        st.markdown('<div class="section-header"><i class="fa-solid fa-fire"></i> Complaint Density Matrix</div>', unsafe_allow_html=True)
        fig_h = chart_complaint_heatmap(df_filt)
        if fig_h:
            st.plotly_chart(fig_h, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("Need source + aspect/topic columns for heatmap.")
    with c7:
        st.markdown('<div class="section-header"><i class="fa-solid fa-triangle-exclamation"></i> High-Urgency Grievances</div>', unsafe_allow_html=True)
        render_urgency_alerts(df_filt, max_alerts=5)


# =============================================================================
# PAGE: TOPICS
# =============================================================================
def page_topics(df_full: pd.DataFrame, df_filt: pd.DataFrame, topic_keywords: dict):
    st.markdown(
        f'<h2 style="font-size:1.5rem;font-weight:700;color:{BRAND["navy"]};margin-bottom:0.25rem">'
        'Topic Intelligence</h2>'
        f'<p style="color:{BRAND["text_secondary"]};font-size:0.875rem;margin-bottom:1.5rem">'
        'Automated topic classification across all customer feedback channels</p>',
        unsafe_allow_html=True,
    )

    if "Topic_Label" not in df_filt.columns:
        st.info("Topic labels not available in the current dataset. Run the NLP pipeline first.")
        return

    # Topic distribution bar
    st.markdown('<div class="section-header"><i class="fa-solid fa-chart-bar"></i> Topic Volume</div>', unsafe_allow_html=True)
    topic_counts = df_filt["Topic_Label"].value_counts().head(12)
    fig_topics   = px.bar(
        x=topic_counts.values, y=topic_counts.index,
        orientation="h",
        color=topic_counts.values,
        color_continuous_scale=[[0, BRAND["neutral_bg"]], [1, BRAND["navy"]]],
        text=topic_counts.values,
    )
    fig_topics.update_traces(textposition="outside", textfont=dict(size=11, color=BRAND["text_secondary"]))
    fig_topics.update_layout(
        **_CHART_LAYOUT,
        xaxis=_axes_style( title="Reviews"),
        yaxis=_axes_style( title=""),
        coloraxis_showscale=False,
        height=350,
        margin=dict(l=0, r=50, t=20, b=0),
    )
    st.plotly_chart(fig_topics, use_container_width=True, config={"displayModeBar": False})

    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="section-header"><i class="fa-solid fa-timeline"></i> Topic Evolution</div>', unsafe_allow_html=True)
        fig_tt = chart_topic_trend(df_filt)
        if fig_tt:
            st.plotly_chart(fig_tt, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("Need date and topic columns.")

    with c2:
        st.markdown('<div class="section-header"><i class="fa-solid fa-magnifying-glass-chart"></i> Topic Deep Dive</div>', unsafe_allow_html=True)
        raw_topics = sorted(df_filt["Topic_Label"].dropna().unique().tolist())
        sel_t = st.selectbox("Select topic", raw_topics, key="topic_deepdive_v2")
        t_df  = df_filt[df_filt["Topic_Label"] == sel_t]

        if not t_df.empty:
            kc1, kc2, kc3 = st.columns(3)
            kc1.metric("Reviews", f"{len(t_df):,}")
            kc2.metric("Positive", f"{pct(t_df, 'Positive'):.1f}%")
            kc3.metric("Negative", f"{pct(t_df, 'Negative'):.1f}%")

            kws = top_keywords(t_df["content"].tolist(), n=12)
            if kws:
                kw_fig = go.Figure(go.Bar(
                    x=[c for _, c in kws], y=[w for w, _ in kws],
                    orientation="h",
                    marker_color=BRAND["navy_light"],
                ))
                kw_fig.update_layout(
                    **_CHART_LAYOUT,
                    xaxis=_axes_style( title="Frequency"),
                    yaxis=_axes_style( title=""),
                    height=250,
                    margin=dict(l=0, r=0, t=10, b=0),
                )
                st.plotly_chart(kw_fig, use_container_width=True, config={"displayModeBar": False})


# =============================================================================
# PAGE: SENTIMENT ANALYSIS
# =============================================================================
def page_sentiment(df_full: pd.DataFrame, df_filt: pd.DataFrame):
    st.markdown(
        f'<h2 style="font-size:1.5rem;font-weight:700;color:{BRAND["navy"]};margin-bottom:0.25rem">'
        'Sentiment Analysis</h2>'
        f'<p style="color:{BRAND["text_secondary"]};font-size:0.875rem;margin-bottom:1.5rem">'
        'AI-powered sentiment scoring via HuggingFace RoBERTa + VADER fallback</p>',
        unsafe_allow_html=True,
    )

    # Row 1: Violin + KWs
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="section-header"><i class="fa-solid fa-wave-square"></i> Rating by Sentiment</div>', unsafe_allow_html=True)
        fig_v = chart_violin(df_filt)
        if fig_v:
            st.plotly_chart(fig_v, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("Need score + ai_sentiment columns.")
    with c2:
        st.markdown('<div class="section-header"><i class="fa-solid fa-magnifying-glass"></i> Keyword Signal Comparison</div>', unsafe_allow_html=True)
        fig_kw = chart_keyword_comparison(df_filt)
        if fig_kw:
            st.plotly_chart(fig_kw, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("Need content + ai_sentiment columns.")

    st.divider()

    # Row 2: Sentiment over time per source
    if "source" in df_filt.columns and "at" in df_filt.columns:
        st.markdown('<div class="section-header"><i class="fa-solid fa-chart-line"></i> Sentiment Score Trajectory by Platform</div>', unsafe_allow_html=True)
        agg_src = (
            df_filt.assign(month=df_filt["at"].dt.to_period("M").dt.start_time)
            .groupby(["month", "source"])["sentiment_score"]
            .mean()
            .reset_index()
        ) if "sentiment_score" in df_filt.columns else None

        if agg_src is not None and not agg_src.empty:
            fig_src = px.line(
                agg_src, x="month", y="sentiment_score", color="source",
                labels={"sentiment_score": "Avg Sentiment Score", "month": ""},
                color_discrete_sequence=[SOURCE_CONFIG.get(s, {}).get("color", BRAND["navy"]) for s in agg_src["source"].unique()],
            )
            fig_src.update_traces(line=dict(width=2.5))
            fig_src.update_layout(
                **_CHART_LAYOUT,
                xaxis=_axes_style(),
                yaxis=_axes_style( zeroline=True, zerolinecolor=BRAND["border"], title="Avg Sentiment Score"),
                legend=dict(title="Platform", orientation="v", font=dict(size=11)),
                height=320,
                hovermode="x unified",
                margin=dict(l=0, r=0, t=20, b=0),
            )
            st.plotly_chart(fig_src, use_container_width=True, config={"displayModeBar": False})


# =============================================================================
# PAGE: ASPECT ANALYSIS
# =============================================================================
def page_aspects(
    df_raw: Optional[pd.DataFrame] = None,
    df_filt: Optional[pd.DataFrame] = None,
    topic_keywords: Optional[dict] = None,
    source_label: str = "Live Pipeline Data",
):
    st.markdown(
        f'<h2 style="font-size:1.5rem;font-weight:700;color:{BRAND["navy"]};margin-bottom:0.25rem">'
        'Aspect-Based Sentiment & Root Cause Intelligence</h2>'
        f'<p style="color:{BRAND["text_secondary"]};font-size:0.875rem;margin-bottom:1.5rem">'
        'Enterprise granular classification powered by Groq LLM (Llama 3.3 70B) & ABSA benchmark</p>',
        unsafe_allow_html=True,
    )

    is_live = (source_label == "Live Pipeline Data")

    # ── Resolve Active Dataset ──────────────────────────────────────────────
    if is_live and df_filt is not None and not df_filt.empty:
        df = df_filt.copy()
        text_col = "content"
        aspect_col = "aspect"
        date_col = "at"
        rating_col = "rating"
        sent_col = "sentiment"
        source_col = "source"
        dataset_subtitle = "Live Multi-Channel Feedback (Supabase PostgreSQL)"
    else:
        raw_h = load_aspect_csv()
        if raw_h is not None and not raw_h.empty:
            df = raw_h.copy()
            text_col = "Review_Text" if "Review_Text" in df.columns else "content"
            aspect_col = "Aspect" if "Aspect" in df.columns else "aspect"
            date_col = "Date" if "Date" in df.columns else "at"
            rating_col = "Rating" if "Rating" in df.columns else "score"
            sent_col = "Sentiment" if "Sentiment" in df.columns else "sentiment"
            source_col = "source" if "source" in df.columns else None
            dataset_subtitle = "Historical Benchmark Dataset (HelloBPCL_Detailed_Analysis.csv)"
        elif df_filt is not None and not df_filt.empty:
            df = df_filt.copy()
            text_col = "content"
            aspect_col = "aspect"
            date_col = "at"
            rating_col = "rating"
            sent_col = "sentiment"
            source_col = "source"
            dataset_subtitle = "Live Multi-Channel Feedback (Supabase PostgreSQL)"
        else:
            st.warning("No review data available for Aspect Analysis.")
            return

    # Standardize to normalized view dataframe
    norm_df = pd.DataFrame()
    norm_df["aspect"] = df[aspect_col].fillna("General").astype(str) if aspect_col in df.columns else "General"
    norm_df["sentiment"] = df[sent_col].fillna("Neutral").astype(str) if sent_col in df.columns else "Neutral"
    norm_df["content"] = df[text_col].fillna("").astype(str) if text_col in df.columns else ""
    norm_df["rating"] = pd.to_numeric(df[rating_col], errors="coerce") if rating_col in df.columns else None
    norm_df["at"] = df[date_col] if date_col in df.columns else None
    norm_df["source"] = df[source_col].fillna("csv") if (source_col and source_col in df.columns) else "csv"
    norm_df["review_id"] = df["review_id"] if "review_id" in df.columns else [f"row_{i}" for i in range(len(df))]
    if "app_version" in df.columns:
        norm_df["app_version"] = df["app_version"]
    elif "App_Version" in df.columns:
        norm_df["app_version"] = df["App_Version"]
    else:
        norm_df["app_version"] = "—"

    # ── Groq LLM Intelligence Suite ─────────────────────────────────────────
    current_key = get_groq_api_key()
    groq_ready = bool(current_key and current_key.startswith("gsk_"))

    if groq_ready:
        st.markdown(
            f"""
            <div style="background:#F0FDF4;border:1px solid #BBF7D0;border-radius:10px;padding:0.75rem 1.25rem;
                        margin-bottom:1.25rem;display:flex;align-items:center;justify-content:space-between">
              <div style="display:flex;align-items:center;gap:10px">
                <i class="fa-solid fa-brain" style="color:#059669;font-size:1.1rem"></i>
                <div>
                  <strong style="color:#065F46;font-size:0.875rem">Groq LPU AI Engine Active</strong>
                  <span style="color:#047857;font-size:0.78rem;margin-left:8px">
                    Model: {DEFAULT_GROQ_MODEL} (Sub-second enterprise inference)
                  </span>
                </div>
              </div>
              <span style="background:#059669;color:#FFFFFF;padding:3px 10px;border-radius:20px;font-size:0.72rem;font-weight:700;letter-spacing:0.04em">
                <i class="fa-solid fa-circle" style="font-size:0.5rem;vertical-align:middle;margin-right:4px"></i>READY
              </span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div style="background:#FFFBEB;border:1px solid #FDE68A;border-radius:10px;padding:0.75rem 1.25rem;
                        margin-bottom:1.25rem;display:flex;align-items:center;justify-content:space-between">
              <div style="display:flex;align-items:center;gap:10px">
                <i class="fa-solid fa-key" style="color:#D97706;font-size:1.1rem"></i>
                <div>
                  <strong style="color:#92400E;font-size:0.875rem">Groq API Key Required for LLM Aspect Categorization</strong>
                  <span style="color:#B45309;font-size:0.78rem;margin-left:8px">
                    Enter your Groq key below to categorize reviews using Llama 3.3 70B
                  </span>
                </div>
              </div>
              <a href="https://console.groq.com/keys" target="_blank"
                 style="background:#D97706;color:#FFFFFF;padding:4px 12px;border-radius:6px;font-size:0.75rem;font-weight:600;text-decoration:none">
                Get Free API Key
              </a>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Expander: Groq Setup & Live Verbatim Tester
    with st.expander("Groq AI Intelligence Configuration & Real-Time Verbatim Tester", expanded=(not groq_ready)):
        g_c1, g_c2 = st.columns([1.2, 1.8])

        with g_c1:
            st.markdown(
                f'<div style="font-size:0.75rem;font-weight:700;color:{BRAND["navy"]};text-transform:uppercase;'
                'letter-spacing:0.06em;margin-bottom:0.5rem"><i class="fa-solid fa-sliders"></i> LLM Configuration</div>',
                unsafe_allow_html=True,
            )
            input_key = st.text_input(
                "Groq API Key",
                value=current_key or "",
                type="password",
                placeholder="gsk_...",
                key="groq_input_key_field",
                help="Enter your Groq API key from console.groq.com",
            )
            sel_model = st.selectbox(
                "Select Model",
                [DEFAULT_GROQ_MODEL, FAST_GROQ_MODEL],
                index=0,
                key="groq_model_sel",
                help="Llama 3.3 70B delivers highest enterprise accuracy; 8B delivers maximum speed.",
            )
            if st.button("Apply API Key", key="save_groq_key_btn"):
                if input_key.strip():
                    st.session_state["groq_api_key"] = input_key.strip()
                    os.environ["GROQ_API_KEY"] = input_key.strip()
                    st.success("Groq API key activated for this session.")
                    st.rerun()
                else:
                    st.warning("Please enter a valid key starting with gsk_.")

        with g_c2:
            st.markdown(
                f'<div style="font-size:0.75rem;font-weight:700;color:{BRAND["navy"]};text-transform:uppercase;'
                'letter-spacing:0.06em;margin-bottom:0.5rem"><i class="fa-solid fa-microscope"></i> Live Verbatim Classifier</div>',
                unsafe_allow_html=True,
            )
            sample_val = (
                "Booked cylinder 8 days ago via Hello BPCL app. Money debited Rs. 850 from SBI account but status still shows Pending. "
                "Delivery boy demanded Rs. 50 extra for delivery."
            )
            test_text = st.text_area(
                "Customer Review / Verbatim",
                value=sample_val,
                height=80,
                key="groq_test_verbatim",
            )

            if st.button("Classify with Groq LLM", key="run_single_groq_test"):
                effective_key = input_key.strip() or current_key
                if not effective_key:
                    st.warning("Please provide a Groq API key above first.")
                else:
                    with st.spinner("Analyzing with Groq LPU engine..."):
                        t0 = time.time()
                        analysis = classify_single_review(test_text, api_key=effective_key, model=sel_model)
                        elapsed = time.time() - t0

                    asp_badge = analysis.get("aspect", "General")
                    sub_asp = analysis.get("sub_aspect", "")
                    sent = analysis.get("sentiment", "Neutral")
                    score = analysis.get("sentiment_score", 0.0)
                    urgency = analysis.get("urgency", "Normal")
                    root_cause = analysis.get("root_cause", "")

                    urg_color = "#DC2626" if urgency == "High" else "#2563EB"
                    urg_bg = "#FEE2E2" if urgency == "High" else "#DBEAFE"

                    st.markdown(
                        f"""
                        <div style="background:{BRAND['card']};border:1.5px solid {BRAND['navy']};border-radius:10px;padding:1rem;margin-top:0.75rem">
                          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:0.5rem;flex-wrap:wrap;gap:6px">
                            <span style="background:{BRAND['navy']};color:#FFFFFF;padding:3px 10px;border-radius:6px;font-size:0.75rem;font-weight:700">
                              <i class="fa-solid fa-tag"></i> {asp_badge}
                            </span>
                            <span style="background:#F1F5F9;color:{BRAND['text_primary']};padding:3px 10px;border-radius:6px;font-size:0.75rem;font-weight:600">
                              {sub_asp}
                            </span>
                            <span style="background:{urg_bg};color:{urg_color};padding:3px 10px;border-radius:6px;font-size:0.75rem;font-weight:700">
                              {urgency} Urgency
                            </span>
                            {sentiment_pill_html(sent)}
                            <span style="font-size:0.72rem;color:{BRAND['text_muted']}">Score: {score:+.2f} &bull; {elapsed*1000:.0f}ms</span>
                          </div>
                          <div style="font-size:0.84rem;color:{BRAND['text_primary']};line-height:1.5">
                            <strong>Root Cause:</strong> {root_cause}
                          </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

    # ── Batch Database Aspect Enricher (Live Data Mode) ─────────────────────
    if is_live and df_raw is not None and not df_raw.empty:
        # Check how many reviews need aspect classification
        gen_mask = (df_raw["aspect"].fillna("").str.lower().isin(["", "general", "none", "unknown"]))
        un_count = int(gen_mask.sum())

        if un_count > 0:
            st.markdown(
                f"""
                <div style="background:{BRAND['card']};border:1.5px solid {BRAND['border']};border-left:4px solid {BRAND['gold']};
                            border-radius:8px;padding:1rem 1.25rem;margin-top:1rem;margin-bottom:1.5rem;
                            display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px">
                  <div>
                    <div style="font-weight:700;color:{BRAND['navy']};font-size:0.95rem">
                      <i class="fa-solid fa-wand-magic-sparkles" style="color:{BRAND['gold']}"></i>
                      Batch Aspect Classification Available ({un_count:,} Reviews)
                    </div>
                    <div style="font-size:0.8rem;color:{BRAND['text_secondary']};margin-top:2px">
                      Currently {un_count:,} reviews have baseline generic classification. Use Groq LLM to categorize them into exact BPCL business verticals & update Supabase PostgreSQL.
                    </div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            bc1, bc2, _ = st.columns([1.5, 1.5, 3])
            with bc1:
                run_test_batch = st.button("Classify 20 Reviews (Quick Test)", key="btn_groq_batch_20")
            with bc2:
                run_full_batch = st.button(f"Classify All {un_count:,} Reviews", key="btn_groq_batch_all")

            if run_test_batch or run_full_batch:
                effective_key = get_groq_api_key()
                if not effective_key:
                    st.error("Please enter a Groq API key in the configuration panel above.")
                else:
                    limit_n = 20 if run_test_batch else un_count
                    subset_df = df_raw[gen_mask].head(limit_n)
                    records_to_enrich = subset_df.to_dict(orient="records")

                    prog_bar = st.progress(0.0)
                    status_txt = st.empty()

                    def on_prog(done, total, msg):
                        frac = min(1.0, done / max(1, total))
                        prog_bar.progress(frac)
                        status_txt.markdown(f'<div style="font-size:0.8rem;color:{BRAND["text_secondary"]}">{msg}</div>', unsafe_allow_html=True)

                    try:
                        enriched = classify_batch_reviews(
                            records_to_enrich,
                            api_key=effective_key,
                            model=DEFAULT_GROQ_MODEL,
                            batch_size=12,
                            progress_callback=on_prog,
                        )

                        # Write updates back to Supabase PostgreSQL
                        db_conn_url = os.environ.get("SUPABASE_DB_URL")
                        if db_conn_url:
                            n_updated = update_supabase_aspects(db_conn_url, enriched)
                            st.success(f"Successfully enriched and updated {n_updated} reviews in Supabase with Groq aspects!")
                            st.cache_data.clear()
                            time.sleep(1.2)
                            st.rerun()
                        else:
                            st.warning("Database URL not found in environment; enriched records locally.")
                    except Exception as b_err:
                        st.error(f"Batch categorization error: {b_err}")

    st.divider()

    # ── Aspect KPIs ──────────────────────────────────────────────────────────
    sentiments = ["All"] + sorted([s for s in norm_df["sentiment"].unique() if s in ("Positive", "Neutral", "Negative")])
    sel_sent = st.radio(
        "Filter by Sentiment",
        sentiments,
        horizontal=True,
        index=0,
        key="aspect_sent_filter_v3",
    )

    fd = norm_df if sel_sent == "All" else norm_df[norm_df["sentiment"] == sel_sent].copy()

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Reviews", f"{len(fd):,}", delta=f"of {len(norm_df):,} in view")
    k2.metric("Active Aspects", f"{fd['aspect'].nunique()}")
    if not fd.empty:
        top_asp_series = fd["aspect"].value_counts()
        top_name = top_asp_series.index[0]
        top_count = top_asp_series.values[0]
        pct = (top_count / max(1, len(fd))) * 100
        k3.metric("Top Aspect", top_name, delta=f"{top_count:,} mentions ({pct:.1f}%)")
    else:
        k3.metric("Top Aspect", "N/A")

    neg_share = (norm_df["sentiment"] == "Negative").sum() / max(1, len(norm_df)) * 100
    k4.metric("Negative Share", f"{neg_share:.1f}%", delta="Critical Focus" if neg_share > 30 else "Normal")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Aspect Distribution Chart ────────────────────────────────────────────
    if not fd.empty:
        asp_counts = fd["aspect"].value_counts().head(12)
        bar_colors = [
            BRAND["negative"] if sel_sent == "Negative" else (
                BRAND["positive"] if sel_sent == "Positive" else BRAND["navy"]
            )
        ] * len(asp_counts)

        fig_asp = go.Figure(
            go.Bar(
                y=asp_counts.index[::-1],
                x=asp_counts.values[::-1],
                orientation="h",
                marker=dict(color=bar_colors[::-1]),
                text=asp_counts.values[::-1],
                textposition="auto",
                hovertemplate="<b>%{y}</b><br>Mentions: %{x:,}<extra></extra>",
            )
        )
        fig_asp.update_layout(
            **_CHART_LAYOUT,
            title=dict(
                text=f"Aspect Mentions Distribution — {sel_sent} Sentiment",
                font=dict(size=14, color=BRAND["text_primary"]),
                x=0,
                xanchor="left",
            ),
            xaxis=_axes_style(title="Review Mentions"),
            yaxis=_axes_style(title=""),
            height=420,
            margin=dict(l=0, r=0, t=50, b=0),
        )
        st.plotly_chart(fig_asp, use_container_width=True, config={"displayModeBar": False})

        st.divider()

        # ── Aspect Drilldown ─────────────────────────────────────────────────
        st.markdown(
            '<div class="section-header"><i class="fa-solid fa-crosshairs"></i> Aspect Drill-Down & Verbatim Inspection</div>',
            unsafe_allow_html=True,
        )

        avail_aspects = sorted(fd["aspect"].unique().tolist())
        d_col1, d_col2 = st.columns([2, 1])
        with d_col1:
            sel_asp = st.selectbox("Select Business Aspect", avail_aspects, key="aspect_drill_sel")
        with d_col2:
            drill_sort = st.selectbox("Sort Verbatims", ["Latest First", "Lowest Rating", "Highest Rating"], key="drill_sort")

        asp_df = fd[fd["aspect"] == sel_asp].copy()

        dc1, dc2, dc3, dc4 = st.columns(4)
        dc1.metric("Aspect Volume", f"{len(asp_df):,}")
        avg_r = asp_df["rating"].mean() if "rating" in asp_df.columns and asp_df["rating"].notna().any() else None
        dc2.metric("Avg Star Rating", f"{avg_r:.2f} / 5" if avg_r else "N/A")
        if "rating" in asp_df.columns and asp_df["rating"].notna().any():
            pos_rt = ((asp_df["rating"] >= 4).sum() / max(1, len(asp_df))) * 100
            neg_rt = ((asp_df["rating"] <= 2).sum() / max(1, len(asp_df))) * 100
            dc3.metric("4-5 Star Share", f"{pos_rt:.0f}%")
            dc4.metric("1-2 Star Share", f"{neg_rt:.0f}%")
        else:
            dc3.metric("4-5 Star Share", "N/A")
            dc4.metric("1-2 Star Share", "N/A")

        st.markdown("<br>", unsafe_allow_html=True)

        # Download button
        csv_data = asp_df.to_csv(index=False)
        st.download_button(
            label=f"Export {sel_asp} Verbatims ({len(asp_df)} rows)",
            data=csv_data,
            file_name=f"bpcl_aspect_{sel_asp.replace(' ', '_').lower()}.csv",
            mime="text/csv",
        )

        # Sort drilldown cards
        if drill_sort == "Latest First" and "at" in asp_df.columns:
            asp_df = asp_df.sort_values("at", ascending=False)
        elif drill_sort == "Lowest Rating" and "rating" in asp_df.columns:
            asp_df = asp_df.sort_values("rating", ascending=True)
        elif drill_sort == "Highest Rating" and "rating" in asp_df.columns:
            asp_df = asp_df.sort_values("rating", ascending=False)

        # Render Review Cards
        for _, row in asp_df.head(15).iterrows():
            rating = int(row["rating"]) if pd.notna(row.get("rating")) else None
            date_s = str(row.get("at", ""))[:10] if pd.notna(row.get("at")) else "—"
            content = str(row.get("content", ""))
            sent = str(row.get("sentiment", "Neutral"))
            stars = star_html(rating)
            s_pill = sentiment_pill_html(sent)
            src = str(row.get("source", "google_play"))

            st.markdown(
                f"""
                <div class="review-card">
                  <div class="review-card-header">
                    {source_badge_html(src)}
                    <span style="display:inline-flex;align-items:center;gap:3px">{stars}</span>
                    {s_pill}
                    <span style="background:#F1F5F9;color:{BRAND['navy']};padding:2px 8px;border-radius:4px;font-size:0.72rem;font-weight:700">
                      {sel_asp}
                    </span>
                  </div>
                  <div class="review-body">{content[:500]}</div>
                  <div class="review-card-meta">
                    <div class="review-card-meta-item">
                      <i class="fa-solid fa-calendar" style="font-size:0.65rem"></i>
                      {date_s}
                    </div>
                    <div class="review-card-meta-item">
                      <i class="fa-solid fa-code-branch" style="font-size:0.65rem"></i>
                      v{row.get("app_version", "—")}
                    </div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )



# =============================================================================
# PAGE: CUSTOMER VOICE EXPLORER
# =============================================================================
def page_explorer(df_filt: pd.DataFrame, topic_keywords: dict):
    st.markdown(
        f'<h2 style="font-size:1.5rem;font-weight:700;color:{BRAND["navy"]};margin-bottom:0.25rem">'
        'Customer Voice Explorer</h2>'
        f'<p style="color:{BRAND["text_secondary"]};font-size:0.875rem;margin-bottom:1.5rem">'
        'Read and search customer verbatims as executive review cards</p>',
        unsafe_allow_html=True,
    )

    # Inline search + sort
    ec1, ec2, ec3 = st.columns([2.5, 1.5, 1])
    with ec1:
        inline_q = st.text_input(
            "Search reviews",
            placeholder='Search keywords, e.g. "OTP not received", "refund"',
            key="explorer_search",
            label_visibility="collapsed",
        )
    with ec2:
        sort_by = st.selectbox(
            "Sort",
            ["Latest First", "Oldest First", "Highest Rating", "Lowest Rating",
             "Most Positive", "Most Negative"],
            label_visibility="collapsed",
            key="explorer_sort",
        )
    with ec3:
        show_n = st.number_input("Show", min_value=5, max_value=100, value=20, step=5,
                                 label_visibility="collapsed", key="explorer_n")

    # Apply inline search
    view_df = df_filt.copy()
    if inline_q:
        view_df = view_df[view_df["content"].str.lower().str.contains(inline_q.lower(), na=False)]

    # Sort
    sort_map = {
        "Latest First":    ("at", False),
        "Oldest First":    ("at", True),
        "Highest Rating":  ("score", False),
        "Lowest Rating":   ("score", True),
        "Most Positive":   ("sentiment_score", False),
        "Most Negative":   ("sentiment_score", True),
    }
    col_s, asc_s = sort_map[sort_by]
    if col_s in view_df.columns:
        view_df = view_df.sort_values(col_s, ascending=asc_s)

    # Result count
    st.markdown(
        f'<div style="font-size:0.82rem;color:{BRAND["text_secondary"]};margin-bottom:1rem">'
        f'<i class="fa-solid fa-filter"></i>  Showing <strong>{min(int(show_n), len(view_df)):,}</strong>'
        f' of <strong>{len(view_df):,}</strong> reviews</div>',
        unsafe_allow_html=True,
    )

    # CSV export
    if not view_df.empty:
        csv_out = view_df.head(int(show_n)).to_csv(index=False)
        st.download_button(
            label=f"Download {min(int(show_n), len(view_df)):,} Reviews as CSV",
            data=csv_out,
            file_name=f"bpcl_reviews_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
        )

    # Cards
    render_review_cards(view_df, max_cards=int(show_n))

    if view_df.empty:
        st.info("No reviews match the current filters and search query.")


# =============================================================================
# PAGE: MARKET BATTLEGROUND (Competitive)
# =============================================================================
def page_market_battleground():
    st.markdown(
        f'<h2 style="font-size:1.5rem;font-weight:700;color:{BRAND["navy"]};margin-bottom:0.25rem">'
        'Market Battleground</h2>'
        f'<p style="color:{BRAND["text_secondary"]};font-size:0.875rem;margin-bottom:1.5rem">'
        'BPCL vs IndianOil vs HPCL vs Shell — Competitive Intelligence</p>',
        unsafe_allow_html=True,
    )

    comp = load_competitive()
    if comp is None:
        st.markdown(
            f'<div style="padding:2rem;text-align:center;background:{BRAND["neutral_bg"]};'
            f'border:1px dashed {BRAND["border_mid"]};border-radius:12px">'
            f'<i class="fa-solid fa-chart-pie" style="font-size:2rem;color:{BRAND["border_mid"]}"></i>'
            f'<div style="margin-top:0.75rem;color:{BRAND["text_secondary"]};font-size:0.875rem">'
            f'Competitive data not found. Run the benchmarking notebook to generate '
            f'<code>competitive_reviews_raw.csv</code>.</div></div>',
            unsafe_allow_html=True,
        )
        return

    # NSS per brand
    cutoff = pd.Timestamp.now() - pd.DateOffset(months=12)
    cf = comp[comp["at"] >= cutoff].copy()

    def brand_nss(brand_df):
        if brand_df.empty:
            return 0
        promoters   = (brand_df["score"] == 5).sum()
        detractors  = (brand_df["score"] <= 3).sum()
        return round((promoters - detractors) / len(brand_df) * 100, 2)

    brands = cf["brand"].unique() if "brand" in cf.columns else []
    nss_by = {b: brand_nss(cf[cf["brand"] == b]) for b in brands}

    bpcl_nss    = nss_by.get("BPCL", 0)
    iocl_nss    = nss_by.get("IndianOil", 0)
    hpcl_nss    = nss_by.get("HPCL", 0)
    shell_nss   = nss_by.get("Shell", 0)
    mkt_avg     = round(np.mean([v for k, v in nss_by.items() if k != "BPCL"]), 2) if len(nss_by) > 1 else 0

    mc1, mc2, mc3, mc4 = st.columns(4)
    mc1.metric("BPCL NSS",        f"{bpcl_nss:+.2f}", delta=f"vs market avg {bpcl_nss - mkt_avg:+.1f}")
    mc2.metric("vs IndianOil",    f"{bpcl_nss - iocl_nss:+.2f}", delta=f"IOCL: {iocl_nss:+.1f}")
    mc3.metric("vs HPCL",         f"{bpcl_nss - hpcl_nss:+.2f}", delta=f"HPCL: {hpcl_nss:+.1f}")
    mc4.metric("vs Shell",        f"{bpcl_nss - shell_nss:+.2f}", delta=f"Shell: {shell_nss:+.1f}")

    st.divider()

    # SOV + Heatmap
    bc1, bc2 = st.columns(2)
    with bc1:
        st.markdown('<div class="section-header"><i class="fa-solid fa-broadcast-tower"></i> Share of Voice</div>', unsafe_allow_html=True)
        if "brand" in cf.columns and "at" in cf.columns:
            sov = cf.groupby([pd.Grouper(key="at", freq="W"), "brand"]).size().reset_index(name="count")
            fig_sov = px.line(
                sov, x="at", y="count", color="brand",
                labels={"at": "", "count": "Weekly Reviews"},
                color_discrete_sequence=px.colors.qualitative.Set1,
            )
            fig_sov.update_traces(line=dict(width=2))
            fig_sov.update_layout(
                **_CHART_LAYOUT,
                xaxis=_axes_style(),
                yaxis=_axes_style(),
                hovermode="x unified",
                height=320,
                margin=dict(l=0, r=0, t=20, b=0),
            )
            st.plotly_chart(fig_sov, use_container_width=True, config={"displayModeBar": False})

    with bc2:
        st.markdown('<div class="section-header"><i class="fa-solid fa-fire"></i> Complaint Heatmap by Brand</div>', unsafe_allow_html=True)
        topics     = ["Login", "Payment", "UI / App", "Support"]
        topic_kws  = {
            "Login":    ["login", "otp", "verify"],
            "Payment":  ["payment", "fail", "money", "deduct"],
            "UI / App": ["slow", "crash", "hang", "freeze"],
            "Support":  ["support", "help", "ticket"],
        }
        rows = []
        for brand in brands:
            bd  = cf[(cf["brand"] == brand) & (cf["score"] <= 2)] if "score" in cf.columns else cf[cf["brand"] == brand]
            row = {"Brand": brand}
            for t in topics:
                cnt = sum(bd["content"].fillna("").str.lower().str.contains(kw).sum() for kw in topic_kws[t]) if "content" in bd.columns else 0
                row[t] = round(cnt / max(len(cf[cf["brand"] == brand]), 1) * 100, 2)
            rows.append(row)
        cm_df = pd.DataFrame(rows).set_index("Brand")
        fig_cm = px.imshow(
            cm_df.values, x=cm_df.columns.tolist(), y=cm_df.index.tolist(),
            color_continuous_scale=[[0, "#FFF5F5"], [1, BRAND["negative"]]],
            text_auto=".1f", aspect="auto",
        )
        fig_cm.update_layout(
            **_CHART_LAYOUT,
            coloraxis_showscale=False,
            height=320,
            margin=dict(l=0, r=0, t=20, b=0),
        )
        st.plotly_chart(fig_cm, use_container_width=True, config={"displayModeBar": False})

    # Blue ocean
    st.divider()
    st.markdown('<div class="section-header"><i class="fa-solid fa-water"></i> Blue Ocean Opportunities</div>', unsafe_allow_html=True)
    blue = {
        "IndianOil": ["Seamless transaction flow", "Battery optimisation", "Faster app launch"],
        "HPCL":      ["Clean UI design language", "Real-time station updates", "Quick onboarding"],
        "Shell":     ["Premium brand perception", "Rich loyalty rewards", "Global UX standards"],
    }
    b1, b2, b3 = st.columns(3)
    for col, (brand, features) in zip([b1, b2, b3], blue.items()):
        items_html = "".join(
            f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;'
            f'font-size:0.82rem">'
            f'<i class="fa-solid fa-circle-check" style="color:{BRAND["positive"]};font-size:0.75rem"></i>'
            f' {f}</div>'
            for f in features
        )
        col.markdown(
            f"""
            <div class="channel-card" style="text-align:left">
              <div style="font-weight:700;font-size:0.95rem;color:{BRAND['navy']};margin-bottom:0.75rem">
                <i class="fa-solid fa-trophy" style="color:{BRAND['gold']}"></i> {brand}
              </div>
              {items_html}
            </div>
            """,
            unsafe_allow_html=True,
        )


# =============================================================================
# PAGE: STRATEGIC DEEP DIVE
# =============================================================================
def page_strategic_deep_dive():
    st.markdown(
        f'<h2 style="font-size:1.5rem;font-weight:700;color:{BRAND["navy"]};margin-bottom:0.25rem">'
        'Strategic Deep Dive</h2>'
        f'<p style="color:{BRAND["text_secondary"]};font-size:0.875rem;margin-bottom:1.5rem">'
        'Head-to-head competitive intelligence: BPCL vs IndianOil</p>',
        unsafe_allow_html=True,
    )
    try:
        from deep_dive_renderer import render_deep_dive_tab
        render_deep_dive_tab()
    except ImportError:
        st.markdown(
            f'<div style="padding:2rem;text-align:center;background:{BRAND["neutral_bg"]};'
            f'border:1px dashed {BRAND["border_mid"]};border-radius:12px">'
            f'<i class="fa-solid fa-code" style="font-size:2rem;color:{BRAND["border_mid"]}"></i>'
            f'<div style="margin-top:0.75rem;color:{BRAND["text_secondary"]};font-size:0.875rem">'
            f'<code>deep_dive_renderer.py</code> not found in the project root.</div></div>',
            unsafe_allow_html=True,
        )


# =============================================================================
# MAIN APP
# =============================================================================
@st.fragment(run_every="10m")
def _live_refresh_banner(source_label: str):
    """Silent 10-minute live DB refresh strip."""
    if source_label != "live":
        return
    try:
        conn = st.connection("postgresql", type="sql")
        s = conn.query("""
            SELECT COUNT(*) AS total,
                   ROUND(AVG(rating)::NUMERIC,2) AS avg_rating,
                   ROUND(AVG(sentiment_score)::NUMERIC,4) AS avg_sent,
                   MAX(created_at) AS latest
            FROM reviews;
        """, ttl=600)
        if s is not None and not s.empty:
            row = s.iloc[0]
            rc1, rc2, rc3, rc4 = st.columns(4)
            rc1.metric("Live Total",    f"{int(row['total']):,}")
            rc2.metric("Avg Rating",    f"{row['avg_rating']:.2f}")
            rc3.metric("Avg Sentiment", f"{row['avg_sent']:.3f}")
            rc4.metric("Latest Entry",  str(row["latest"])[:10] if row["latest"] else "—")
    except Exception:
        pass


def main():
    mode = st.session_state.get("dataset_mode", "Live Pipeline Data")
    df_raw, source_label = load_data(mode=mode)
    topic_kws = load_topic_keywords()

    if df_raw is None:
        st.error(
            "No data source found. Configure Supabase credentials in Streamlit secrets "
            "or place df_final_enriched.csv in the project root.",
        )
        st.stop()

    # Sidebar + filters
    filters   = render_sidebar(df_raw, source_label)
    df_filt   = apply_filters(df_raw, filters)

    # Live fragment (only fires when DB active)
    _live_refresh_banner(source_label)

    # ── Main tab structure ─────────────────────────────────────────────────────
    tab1, tab2, tab3 = st.tabs([
        "Internal Pulse",
        "Market Battleground",
        "Strategic Deep Dive",
    ])

    with tab1:
        # Sub-navigation inside Internal Pulse
        sub = st.radio(
            "View",
            ["Overview", "Topics", "Sentiment", "Aspects", "Voice Explorer"],
            horizontal=True,
            label_visibility="collapsed",
            key="internal_subnav",
        )

        if sub == "Overview":
            page_overview(df_raw, df_filt, source_label)
        elif sub == "Topics":
            page_topics(df_raw, df_filt, topic_kws)
        elif sub == "Sentiment":
            page_sentiment(df_raw, df_filt)
        elif sub == "Aspects":
            page_aspects(df_raw, df_filt, topic_kws, source_label)
        elif sub == "Voice Explorer":
            page_explorer(df_filt, topic_kws)

    with tab2:
        page_market_battleground()

    with tab3:
        page_strategic_deep_dive()

    # ── Footer ─────────────────────────────────────────────────────────────────
    st.markdown(
        f"""
        <div style="margin-top:3rem;padding:1.25rem 0;border-top:1px solid {BRAND['border']};
                    display:flex;align-items:center;justify-content:space-between">
          <div style="font-size:0.75rem;color:{BRAND['text_muted']}">
            BPCL Customer Intelligence Platform &bull; Voice of Customer Analytics
          </div>
          <div style="font-size:0.75rem;color:{BRAND['text_muted']}">
            Built by Atharv Patil &bull;
            <i class="fa-brands fa-python"></i> Streamlit &nbsp;
            <i class="fa-solid fa-chart-pie"></i> Plotly &nbsp;
            <i class="fa-brands fa-google"></i> HuggingFace
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
