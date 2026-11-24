-- ============================================================
-- BPCL Voice of Customer — PostgreSQL Schema (Supabase)
-- ============================================================
-- Run this entire script in Supabase > SQL Editor > New Query
-- ============================================================

-- Enable UUID generation (already on by default in Supabase)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
-- REVIEWS TABLE
-- Primary key: review_id (VARCHAR) → idempotent upserts via
--   ON CONFLICT (review_id) DO NOTHING
-- ============================================================
CREATE TABLE IF NOT EXISTS public.reviews (
    -- Identity
    review_id           VARCHAR(512)    PRIMARY KEY,
    source              VARCHAR(64)     NOT NULL,           -- 'google_play' | 'app_store' | 'reddit' | 'youtube' | 'twitter' | 'instagram' | 'consumer_forum'
    channel_type        VARCHAR(64)     NOT NULL,           -- 'app_review' | 'social' | 'forum' | 'video_comment'
    app_name            VARCHAR(128),                       -- 'Hello BPCL' | 'BPCL SmartFleet' | NULL

    -- Author
    user_name           TEXT,
    user_image_url      TEXT,

    -- Content
    content             TEXT            NOT NULL,
    processed_text      TEXT,
    rating              NUMERIC(3,1),                       -- 1.0–5.0 for app reviews, NULL for social

    -- Engagement
    thumbs_up_count     INTEGER         DEFAULT 0,
    reply_content       TEXT,
    replied_at          TIMESTAMPTZ,

    -- NLP Enrichment
    sentiment           VARCHAR(16),                        -- 'Positive' | 'Neutral' | 'Negative'
    sentiment_score     NUMERIC(5,4),                       -- -1.0000 to 1.0000
    ai_compound         NUMERIC(5,4),
    ai_confidence       NUMERIC(5,4),
    dominant_topic      INTEGER,
    topic               VARCHAR(128),                       -- human-readable topic label
    aspect              VARCHAR(128),                       -- primary aspect (e.g. 'LPG Delivery')

    -- Versioning
    app_version         VARCHAR(64),

    -- Raw payload (for auditability / re-processing)
    raw_metadata        JSONB           DEFAULT '{}',

    -- Timestamps
    created_at          TIMESTAMPTZ     NOT NULL,           -- when the review was originally posted
    ingested_at         TIMESTAMPTZ     NOT NULL DEFAULT NOW()  -- when our pipeline first stored it
);

-- ============================================================
-- PERFORMANCE INDEXES
-- ============================================================

-- Time-series queries (most common dashboard access pattern)
CREATE INDEX IF NOT EXISTS idx_reviews_created_at
    ON public.reviews (created_at DESC);

-- Sentiment filter
CREATE INDEX IF NOT EXISTS idx_reviews_sentiment
    ON public.reviews (sentiment);

-- Source breakdown
CREATE INDEX IF NOT EXISTS idx_reviews_source
    ON public.reviews (source);

-- Topic drill-down
CREATE INDEX IF NOT EXISTS idx_reviews_topic
    ON public.reviews (topic);

-- Composite: source + date (for per-platform time-series)
CREATE INDEX IF NOT EXISTS idx_reviews_source_created
    ON public.reviews (source, created_at DESC);

-- Composite: topic + sentiment (for heatmap queries)
CREATE INDEX IF NOT EXISTS idx_reviews_topic_sentiment
    ON public.reviews (topic, sentiment);

-- App name (multi-app filtering)
CREATE INDEX IF NOT EXISTS idx_reviews_app_name
    ON public.reviews (app_name);

-- Full-text search on review content (optional but powerful)
CREATE INDEX IF NOT EXISTS idx_reviews_content_fts
    ON public.reviews USING GIN (to_tsvector('english', COALESCE(content, '')));

-- ============================================================
-- PIPELINE METADATA TABLE
-- Tracks each ingestion run for observability / debugging
-- ============================================================
CREATE TABLE IF NOT EXISTS public.pipeline_runs (
    run_id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    run_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    source              VARCHAR(64),
    records_fetched     INTEGER         DEFAULT 0,
    records_inserted    INTEGER         DEFAULT 0,
    status              VARCHAR(16)     DEFAULT 'success',  -- 'success' | 'partial' | 'failed'
    error_message       TEXT,
    duration_seconds    NUMERIC(8,2)
);

-- ============================================================
-- ROW-LEVEL SECURITY (Supabase best practice)
-- Dashboard reads publicly; writes only via service role key.
-- ============================================================
ALTER TABLE public.reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.pipeline_runs ENABLE ROW LEVEL SECURITY;

-- Allow anonymous / authenticated dashboard reads
CREATE POLICY "Allow public read on reviews"
    ON public.reviews FOR SELECT
    USING (true);

-- Allow service-role writes (pipeline uses service role key)
CREATE POLICY "Allow service role insert on reviews"
    ON public.reviews FOR INSERT
    WITH CHECK (true);

CREATE POLICY "Allow public read on pipeline_runs"
    ON public.pipeline_runs FOR SELECT
    USING (true);

CREATE POLICY "Allow service role insert on pipeline_runs"
    ON public.pipeline_runs FOR INSERT
    WITH CHECK (true);

-- ============================================================
-- HELPFUL VIEWS FOR THE STREAMLIT DASHBOARD
-- ============================================================

-- Sentiment summary by source
CREATE OR REPLACE VIEW public.v_sentiment_by_source AS
SELECT
    source,
    sentiment,
    COUNT(*)                                        AS review_count,
    ROUND(AVG(sentiment_score)::NUMERIC, 4)         AS avg_score,
    ROUND(AVG(rating)::NUMERIC, 2)                  AS avg_rating
FROM public.reviews
GROUP BY source, sentiment;

-- Monthly sentiment trend
CREATE OR REPLACE VIEW public.v_monthly_trend AS
SELECT
    DATE_TRUNC('month', created_at)                 AS month,
    source,
    sentiment,
    COUNT(*)                                        AS review_count,
    ROUND(AVG(sentiment_score)::NUMERIC, 4)         AS avg_score
FROM public.reviews
GROUP BY DATE_TRUNC('month', created_at), source, sentiment
ORDER BY month DESC;

-- Topic distribution
CREATE OR REPLACE VIEW public.v_topic_distribution AS
SELECT
    topic,
    sentiment,
    COUNT(*)                                        AS review_count,
    ROUND(AVG(sentiment_score)::NUMERIC, 4)         AS avg_score
FROM public.reviews
WHERE topic IS NOT NULL
GROUP BY topic, sentiment
ORDER BY review_count DESC;

-- ============================================================
-- VERIFY SETUP
-- ============================================================
-- SELECT table_name FROM information_schema.tables
-- WHERE table_schema = 'public'
-- ORDER BY table_name;
