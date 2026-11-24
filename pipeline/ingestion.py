"""
BPCL VoC — Multi-Source Ingestion Engine
==========================================
Scrapers for:
  1. Google Play Store  (google-play-scraper)
  2. Apple App Store    (app-store-scraper)
  3. Reddit             (praw)
  4. YouTube Comments   (google-api-python-client)
  5. Twitter/X          (twscrape + RSS fallback)
  6. Instagram          (instaloader)
  7. Consumer Forum     (requests + BeautifulSoup)

Each scraper is wrapped in its own try/except so a single failure
never aborts the whole pipeline.

Incremental ingestion: every scraper queries the DB for the most
recent `created_at` for that source and only fetches newer records.
"""

from __future__ import annotations

import hashlib
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Generator

import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_review_id(*parts: str) -> str:
    """Deterministic SHA-256-based review_id from source-unique fields."""
    raw = "|".join(str(p) for p in parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:64]


def _now_utc() -> datetime:
    return datetime.now(tz=timezone.utc)


def _get_latest_ts(conn, source: str) -> datetime:
    """
    Returns the most recent `created_at` for a given source from the DB.
    Falls back to 90 days ago so the first run seeds reasonable history.
    """
    from datetime import timedelta

    fallback = _now_utc() - timedelta(days=90)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT MAX(created_at) FROM reviews WHERE source = %s",
                (source,),
            )
            row = cur.fetchone()
            if row and row[0]:
                return row[0].replace(tzinfo=timezone.utc)
    except Exception as exc:
        logger.warning("Could not read latest_ts for %s: %s", source, exc)
    return fallback


# ---------------------------------------------------------------------------
# 1. Google Play Store
# ---------------------------------------------------------------------------
GOOGLE_PLAY_APPS = [
    {"app_id": "com.cgt.bharatgas", "app_name": "Hello BPCL"},
    {"app_id": "com.bpcl.smartfleet", "app_name": "BPCL SmartFleet"},
]


def scrape_google_play(conn) -> list[dict]:
    """Fetch new Google Play reviews for Hello BPCL and BPCL SmartFleet."""
    records: list[dict] = []
    try:
        from google_play_scraper import Sort, reviews as gp_reviews

        for app in GOOGLE_PLAY_APPS:
            latest_ts = _get_latest_ts(conn, "google_play")
            logger.info("Google Play: fetching %s since %s", app["app_name"], latest_ts)
            try:
                result, _ = gp_reviews(
                    app["app_id"],
                    lang="en",
                    country="in",
                    sort=Sort.NEWEST,
                    count=500,
                )
                for r in result:
                    if r.get("at") and r["at"].replace(tzinfo=timezone.utc) <= latest_ts:
                        continue  # already ingested
                    records.append(
                        {
                            "review_id": r.get("reviewId") or _make_review_id("google_play", app["app_id"], str(r.get("at"))),
                            "source": "google_play",
                            "channel_type": "app_review",
                            "app_name": app["app_name"],
                            "user_name": r.get("userName", ""),
                            "user_image_url": r.get("userImage", ""),
                            "content": r.get("content", ""),
                            "rating": r.get("score"),
                            "thumbs_up_count": r.get("thumbsUpCount", 0),
                            "reply_content": r.get("replyContent", ""),
                            "replied_at": r.get("repliedAt"),
                            "app_version": r.get("appVersion", ""),
                            "created_at": r.get("at") or _now_utc(),
                            "raw_metadata": {
                                "reviewCreatedVersion": r.get("reviewCreatedVersion"),
                            },
                        }
                    )
                logger.info("Google Play %s: %d new records", app["app_name"], len(records))
            except Exception as exc:
                logger.error("Google Play scraper failed for %s: %s", app["app_name"], exc)
    except ImportError:
        logger.error("google-play-scraper not installed. Run: pip install google-play-scraper")
    return records


# ---------------------------------------------------------------------------
# 2. Apple App Store (iOS)
# ---------------------------------------------------------------------------
IOS_APP_ID = "1472380988"  # Hello BPCL iOS App ID – verify at apps.apple.com


def scrape_app_store(conn) -> list[dict]:
    """Fetch new App Store reviews for Hello BPCL (iOS)."""
    records: list[dict] = []
    try:
        from app_store_scraper import AppStore

        latest_ts = _get_latest_ts(conn, "app_store")
        logger.info("App Store: fetching Hello BPCL since %s", latest_ts)
        try:
            app = AppStore(country="in", app_name="hello-bpcl", app_id=IOS_APP_ID)
            app.review(how_many=200)
            for r in app.reviews:
                ts = r.get("date")
                if ts:
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=timezone.utc)
                    if ts <= latest_ts:
                        continue
                records.append(
                    {
                        "review_id": _make_review_id("app_store", str(r.get("userName", "")), str(r.get("date", ""))),
                        "source": "app_store",
                        "channel_type": "app_review",
                        "app_name": "Hello BPCL",
                        "user_name": r.get("userName", ""),
                        "content": r.get("review", ""),
                        "rating": r.get("rating"),
                        "created_at": ts or _now_utc(),
                        "raw_metadata": {"title": r.get("title", "")},
                    }
                )
            logger.info("App Store Hello BPCL: %d new records", len(records))
        except Exception as exc:
            logger.error("App Store scraper failed: %s", exc)
    except ImportError:
        logger.error("app-store-scraper not installed. Run: pip install app-store-scraper")
    return records


# ---------------------------------------------------------------------------
# 3. Reddit
# ---------------------------------------------------------------------------
REDDIT_SEARCHES = [
    {"subreddit": "CarsIndia", "query": "BPCL Speed petrol"},
    {"subreddit": "CreditCardsIndia", "query": "SBI BPCL Octane"},
    {"subreddit": "india", "query": "BPCL LPG Bharatgas"},
    {"subreddit": "india", "query": "Hello BPCL app"},
    {"subreddit": "CarsIndia", "query": "BPCL fuel quality"},
]


def scrape_reddit(conn) -> list[dict]:
    """Fetch Reddit posts & top comments mentioning BPCL."""
    records: list[dict] = []
    try:
        import praw

        client_id = os.environ.get("REDDIT_CLIENT_ID", "")
        client_secret = os.environ.get("REDDIT_CLIENT_SECRET", "")
        user_agent = os.environ.get("REDDIT_USER_AGENT", "BPCL-VoC-Bot/1.0 (by /u/bpcl_voc_bot)")

        if not client_id or not client_secret:
            logger.error("Reddit credentials missing. Set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET.")
            return records

        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent,
            read_only=True,
        )

        latest_ts = _get_latest_ts(conn, "reddit")

        for search_cfg in REDDIT_SEARCHES:
            subreddit_name = search_cfg["subreddit"]
            query = search_cfg["query"]
            try:
                subreddit = reddit.subreddit(subreddit_name)
                for submission in subreddit.search(query, sort="new", limit=50):
                    post_ts = datetime.fromtimestamp(submission.created_utc, tz=timezone.utc)
                    if post_ts <= latest_ts:
                        continue

                    # Include post itself as a review
                    post_text = (submission.title or "") + "\n\n" + (submission.selftext or "")
                    if post_text.strip():
                        records.append(
                            {
                                "review_id": _make_review_id("reddit", submission.id, "post"),
                                "source": "reddit",
                                "channel_type": "social",
                                "user_name": str(submission.author) if submission.author else "[deleted]",
                                "content": post_text.strip(),
                                "rating": None,
                                "thumbs_up_count": submission.score,
                                "created_at": post_ts,
                                "raw_metadata": {
                                    "subreddit": subreddit_name,
                                    "post_id": submission.id,
                                    "url": f"https://reddit.com{submission.permalink}",
                                    "query": query,
                                },
                            }
                        )

                    # Top-level comments
                    submission.comments.replace_more(limit=0)
                    for comment in submission.comments.list()[:20]:
                        c_ts = datetime.fromtimestamp(comment.created_utc, tz=timezone.utc)
                        if c_ts <= latest_ts or not comment.body or comment.body == "[deleted]":
                            continue
                        records.append(
                            {
                                "review_id": _make_review_id("reddit", comment.id, "comment"),
                                "source": "reddit",
                                "channel_type": "social",
                                "user_name": str(comment.author) if comment.author else "[deleted]",
                                "content": comment.body,
                                "rating": None,
                                "thumbs_up_count": comment.score,
                                "created_at": c_ts,
                                "raw_metadata": {
                                    "subreddit": subreddit_name,
                                    "post_id": submission.id,
                                    "comment_id": comment.id,
                                    "query": query,
                                },
                            }
                        )

                logger.info("Reddit r/%s '%s': found records so far: %d", subreddit_name, query, len(records))
                time.sleep(1)  # polite rate-limiting
            except Exception as exc:
                logger.error("Reddit search failed for r/%s '%s': %s", subreddit_name, query, exc)
    except ImportError:
        logger.error("praw not installed. Run: pip install praw")
    return records


# ---------------------------------------------------------------------------
# 4. YouTube Comments
# ---------------------------------------------------------------------------
YOUTUBE_SEARCH_QUERIES = [
    "BPCL Hello BPCL app review",
    "Bharatgas LPG delivery review India",
    "UFill BPCL petrol review",
    "BPCL petrol pump experience India",
]
YOUTUBE_COMMENT_LIMIT = 100  # per video


def scrape_youtube(conn) -> list[dict]:
    """Fetch comments from top BPCL-related YouTube videos."""
    records: list[dict] = []
    api_key = os.environ.get("YOUTUBE_API_KEY", "")
    if not api_key:
        logger.error("YouTube API key missing. Set YOUTUBE_API_KEY.")
        return records

    try:
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError

        youtube = build("youtube", "v3", developerKey=api_key)
        latest_ts = _get_latest_ts(conn, "youtube")

        video_ids_seen: set[str] = set()

        for query in YOUTUBE_SEARCH_QUERIES:
            try:
                # Search for videos
                search_resp = (
                    youtube.search()
                    .list(q=query, part="id,snippet", type="video", maxResults=5, relevanceLanguage="en", regionCode="IN")
                    .execute()
                )
                for item in search_resp.get("items", []):
                    video_id = item["id"].get("videoId")
                    if not video_id or video_id in video_ids_seen:
                        continue
                    video_ids_seen.add(video_id)

                    try:
                        comments_resp = (
                            youtube.commentThreads()
                            .list(
                                part="snippet",
                                videoId=video_id,
                                maxResults=YOUTUBE_COMMENT_LIMIT,
                                order="time",
                                textFormat="plainText",
                            )
                            .execute()
                        )
                        for thread in comments_resp.get("items", []):
                            top = thread["snippet"]["topLevelComment"]["snippet"]
                            raw_ts = top.get("publishedAt", "")
                            ts = datetime.fromisoformat(raw_ts.replace("Z", "+00:00")) if raw_ts else _now_utc()
                            if ts <= latest_ts:
                                continue
                            records.append(
                                {
                                    "review_id": _make_review_id("youtube", thread["id"]),
                                    "source": "youtube",
                                    "channel_type": "video_comment",
                                    "user_name": top.get("authorDisplayName", ""),
                                    "user_image_url": top.get("authorProfileImageUrl", ""),
                                    "content": top.get("textDisplay", ""),
                                    "rating": None,
                                    "thumbs_up_count": top.get("likeCount", 0),
                                    "created_at": ts,
                                    "raw_metadata": {
                                        "video_id": video_id,
                                        "video_title": item["snippet"].get("title", ""),
                                        "query": query,
                                    },
                                }
                            )
                        time.sleep(0.5)
                    except HttpError as exc:
                        logger.error("YouTube comments error for video %s: %s", video_id, exc)
            except HttpError as exc:
                logger.error("YouTube search error for query '%s': %s", query, exc)

        logger.info("YouTube: %d new records", len(records))
    except ImportError:
        logger.error("google-api-python-client not installed. Run: pip install google-api-python-client")
    return records


# ---------------------------------------------------------------------------
# 5. Twitter / X — RSS fallback (no login required)
# ---------------------------------------------------------------------------
TWITTER_RSS_FEEDS = [
    "https://nitter.net/search/rss?q=%40BPCLimited&f=tweets",
    "https://nitter.net/search/rss?q=%23Bharatgas&f=tweets",
    "https://nitter.net/search/rss?q=%23HelloBPCL&f=tweets",
    "https://nitter.net/search/rss?q=BPCL+petrol&f=tweets",
]


def scrape_twitter(conn) -> list[dict]:
    """
    Scrapes Twitter/X mentions via public Nitter RSS feeds.
    Falls back gracefully if Nitter is unavailable.
    twscrape (authenticated) is the preferred method but requires
    a Twitter account; RSS is the zero-config fallback.
    """
    records: list[dict] = []
    latest_ts = _get_latest_ts(conn, "twitter")

    # --- Method A: twscrape (authenticated, more reliable) ---
    try:
        import asyncio
        import twscrape  # noqa: F401

        tw_user = os.environ.get("TWITTER_USERNAME", "")
        tw_pass = os.environ.get("TWITTER_PASSWORD", "")

        if tw_user and tw_pass:
            async def _fetch_tweets():
                api = twscrape.API()
                await api.pool.add_account(tw_user, tw_pass, tw_user, tw_pass)
                await api.pool.login_all()
                queries = ["@BPCLimited", "#Bharatgas", "#HelloBPCL", "BPCL app"]
                tw_records = []
                for q in queries:
                    async for tweet in api.search(q, limit=50):
                        ts = tweet.date.replace(tzinfo=timezone.utc) if tweet.date.tzinfo is None else tweet.date
                        if ts <= latest_ts:
                            continue
                        tw_records.append({
                            "review_id": _make_review_id("twitter", str(tweet.id)),
                            "source": "twitter",
                            "channel_type": "social",
                            "user_name": tweet.user.username if tweet.user else "",
                            "content": tweet.rawContent or "",
                            "rating": None,
                            "thumbs_up_count": tweet.likeCount or 0,
                            "created_at": ts,
                            "raw_metadata": {
                                "tweet_id": tweet.id,
                                "retweet_count": tweet.retweetCount,
                                "query": q,
                            },
                        })
                return tw_records

            loop = asyncio.new_event_loop()
            records = loop.run_until_complete(_fetch_tweets())
            loop.close()
            logger.info("Twitter (twscrape): %d new records", len(records))
            return records
    except (ImportError, Exception) as exc:
        logger.warning("twscrape unavailable, falling back to RSS: %s", exc)

    # --- Method B: Nitter RSS fallback ---
    try:
        import feedparser

        for feed_url in TWITTER_RSS_FEEDS:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries:
                    # Parse published date
                    published = entry.get("published_parsed")
                    if published:
                        ts = datetime(*published[:6], tzinfo=timezone.utc)
                    else:
                        ts = _now_utc()

                    if ts <= latest_ts:
                        continue

                    records.append(
                        {
                            "review_id": _make_review_id("twitter_rss", entry.get("id", entry.get("link", ""))),
                            "source": "twitter",
                            "channel_type": "social",
                            "user_name": entry.get("author", ""),
                            "content": entry.get("summary", entry.get("title", "")),
                            "rating": None,
                            "thumbs_up_count": 0,
                            "created_at": ts,
                            "raw_metadata": {
                                "feed_url": feed_url,
                                "link": entry.get("link", ""),
                            },
                        }
                    )
                time.sleep(1)
            except Exception as exc:
                logger.error("Twitter RSS feed failed (%s): %s", feed_url, exc)
    except ImportError:
        logger.error("feedparser not installed. Run: pip install feedparser")

    logger.info("Twitter (RSS): %d new records", len(records))
    return records


# ---------------------------------------------------------------------------
# 6. Instagram — instaloader (public posts only)
# ---------------------------------------------------------------------------
INSTAGRAM_USERNAME = "bpclimited"


def scrape_instagram(conn) -> list[dict]:
    """
    Fetch recent comments on @bpclimited posts.
    NOTE: Requires a logged-in Instagram session for comment access.
    Set IG_USERNAME and IG_PASSWORD in environment.
    """
    records: list[dict] = []
    ig_user = os.environ.get("IG_USERNAME", "")
    ig_pass = os.environ.get("IG_PASSWORD", "")

    if not ig_user or not ig_pass:
        logger.warning("Instagram credentials not set (IG_USERNAME, IG_PASSWORD). Skipping.")
        return records

    try:
        import instaloader

        L = instaloader.Instaloader()
        try:
            L.login(ig_user, ig_pass)
        except instaloader.exceptions.BadCredentialsException:
            logger.error("Instagram login failed: bad credentials.")
            return records
        except Exception as exc:
            logger.error("Instagram login failed: %s", exc)
            return records

        latest_ts = _get_latest_ts(conn, "instagram")

        try:
            profile = instaloader.Profile.from_username(L.context, INSTAGRAM_USERNAME)
            post_count = 0
            for post in profile.get_posts():
                if post_count >= 10:  # only 10 most recent posts
                    break
                post_count += 1
                try:
                    for comment in post.get_comments():
                        ts = comment.created_at_utc.replace(tzinfo=timezone.utc)
                        if ts <= latest_ts:
                            continue
                        records.append(
                            {
                                "review_id": _make_review_id("instagram", str(comment.id)),
                                "source": "instagram",
                                "channel_type": "social",
                                "user_name": comment.owner.username,
                                "content": comment.text,
                                "rating": None,
                                "thumbs_up_count": comment.likes_count if hasattr(comment, "likes_count") else 0,
                                "created_at": ts,
                                "raw_metadata": {
                                    "post_shortcode": post.shortcode,
                                    "post_url": f"https://www.instagram.com/p/{post.shortcode}/",
                                },
                            }
                        )
                except Exception as exc:
                    logger.error("Instagram comment fetch failed for post %s: %s", post.shortcode, exc)
                time.sleep(2)  # polite delay
        except Exception as exc:
            logger.error("Instagram profile fetch failed: %s", exc)
    except ImportError:
        logger.error("instaloader not installed. Run: pip install instaloader")

    logger.info("Instagram: %d new records", len(records))
    return records


# ---------------------------------------------------------------------------
# 7. Consumer Complaints Forum (ConsumerComplaints.in)
# ---------------------------------------------------------------------------
CONSUMER_FORUM_URLS = [
    "https://www.consumercomplaints.in/?company=bpcl&category=&status=&sort=newest",
    "https://www.consumercomplaints.in/?company=bharatgas&category=&status=&sort=newest",
]


def scrape_consumer_forum(conn) -> list[dict]:
    """Scrape BPCL complaints from consumercomplaints.in."""
    records: list[dict] = []
    latest_ts = _get_latest_ts(conn, "consumer_forum")

    try:
        from bs4 import BeautifulSoup

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }

        for url in CONSUMER_FORUM_URLS:
            try:
                resp = requests.get(url, headers=headers, timeout=15)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")

                # Each complaint is a <div class="complaint-item"> or similar
                # Adapt selectors to the actual page structure
                complaint_blocks = soup.select("div.complaint-box, div.review-box, article.complaint")

                if not complaint_blocks:
                    # Fallback: try to find any complaint-like containers
                    complaint_blocks = soup.select("div[class*='complaint']")

                for block in complaint_blocks:
                    try:
                        title_el = block.select_one("h2, h3, .complaint-title, .title")
                        body_el = block.select_one("p, .complaint-body, .description")
                        date_el = block.select_one("time, .date, .posted-on, [datetime]")
                        user_el = block.select_one(".username, .author, .user-name")

                        title = title_el.get_text(strip=True) if title_el else ""
                        body = body_el.get_text(strip=True) if body_el else ""
                        content = f"{title}\n{body}".strip()
                        if not content:
                            continue

                        # Parse date
                        ts = _now_utc()
                        if date_el:
                            dt_str = date_el.get("datetime", date_el.get_text(strip=True))
                            try:
                                from dateutil import parser as dateutil_parser
                                ts = dateutil_parser.parse(dt_str).replace(tzinfo=timezone.utc)
                            except Exception:
                                pass

                        if ts <= latest_ts:
                            continue

                        user = user_el.get_text(strip=True) if user_el else "Anonymous"
                        link_el = block.select_one("a[href]")
                        link = link_el["href"] if link_el else url

                        records.append(
                            {
                                "review_id": _make_review_id("consumer_forum", link, content[:100]),
                                "source": "consumer_forum",
                                "channel_type": "forum",
                                "user_name": user,
                                "content": content,
                                "rating": None,
                                "created_at": ts,
                                "raw_metadata": {"url": link, "source_url": url},
                            }
                        )
                    except Exception as exc:
                        logger.error("Failed to parse complaint block: %s", exc)

                time.sleep(2)
            except Exception as exc:
                logger.error("Consumer forum scrape failed for %s: %s", url, exc)
    except ImportError:
        logger.error("beautifulsoup4 not installed. Run: pip install beautifulsoup4 lxml")

    logger.info("Consumer Forum: %d new records", len(records))
    return records


# ---------------------------------------------------------------------------
# Public API — called by run_daily.py
# ---------------------------------------------------------------------------

SCRAPERS = {
    "google_play": scrape_google_play,
    "app_store": scrape_app_store,
    "reddit": scrape_reddit,
    "youtube": scrape_youtube,
    "twitter": scrape_twitter,
    "instagram": scrape_instagram,
    "consumer_forum": scrape_consumer_forum,
}


def run_all_scrapers(conn) -> dict[str, list[dict]]:
    """
    Run every scraper independently. If one fails, the pipeline continues.
    Returns a dict mapping source_name → list of raw review dicts.
    """
    results: dict[str, list[dict]] = {}
    for name, func in SCRAPERS.items():
        logger.info("=" * 60)
        logger.info("Starting scraper: %s", name.upper())
        try:
            records = func(conn)
            results[name] = records
            logger.info("Scraper %s finished: %d records", name, len(records))
        except Exception as exc:
            logger.error("FATAL error in scraper %s (skipping): %s", name, exc)
            results[name] = []
    return results
