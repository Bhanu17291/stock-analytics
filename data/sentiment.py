# data/sentiment.py
import logging
import time
from datetime import datetime, timezone
from functools import lru_cache

import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer

from data.fetcher import fetch_news

logger = logging.getLogger(__name__)

# ── Download VADER lexicon once at import time ────────────────────────────────
try:
    nltk.data.find("sentiment/vader_lexicon.zip")
except LookupError:
    logger.info("Downloading VADER lexicon...")
    nltk.download("vader_lexicon", quiet=True)


# ── Singleton SIA — created once, reused forever ──────────────────────────────
@lru_cache(maxsize=1)
def _get_sia() -> SentimentIntensityAnalyzer:
    """Return a single shared SentimentIntensityAnalyzer instance."""
    return SentimentIntensityAnalyzer()


# ── Recency helpers ───────────────────────────────────────────────────────────

def _recency_weight(published: str, half_life_hours: float = 24.0) -> float:
    """
    Compute an exponential decay weight based on article age.

    Articles published now → weight 1.0
    Articles published `half_life_hours` ago → weight 0.5
    Articles with unparseable dates → weight 0.5 (neutral fallback)

    Args:
        published:        ISO-8601 date string from the news API.
        half_life_hours:  Time in hours at which weight halves (default 24h).
    """
    if not published:
        return 0.5

    try:
        # Handle both "2024-06-01T10:00:00Z" and plain timestamps
        if published.isdigit():
            pub_dt = datetime.fromtimestamp(int(published), tz=timezone.utc)
        else:
            pub_dt = datetime.fromisoformat(published.replace("Z", "+00:00"))

        age_hours = (datetime.now(tz=timezone.utc) - pub_dt).total_seconds() / 3600
        weight    = 0.5 ** (age_hours / half_life_hours)
        return max(0.05, min(1.0, weight))   # clamp to [0.05, 1.0]

    except (ValueError, OSError):
        logger.debug("Could not parse published date: %s", published)
        return 0.5


# ── Core sentiment analysis ───────────────────────────────────────────────────

def analyze_sentiment(text: str) -> dict:
    """
    Analyze sentiment of a given text using the shared VADER instance.

    Returns compound, pos, neg, neu scores plus a human label and Bootstrap color.
    """
    if not text or not text.strip():
        return {
            "compound": 0.0, "positive": 0.0,
            "negative": 0.0, "neutral":  1.0,
            "label": "Neutral", "color": "warning",
        }

    sia    = _get_sia()
    scores = sia.polarity_scores(text)

    compound = scores["compound"]
    if compound >= 0.05:
        label, color = "Positive", "success"
    elif compound <= -0.05:
        label, color = "Negative", "danger"
    else:
        label, color = "Neutral",  "warning"

    return {
        "compound": round(compound,       4),
        "positive": round(scores["pos"],  4),
        "negative": round(scores["neg"],  4),
        "neutral":  round(scores["neu"],  4),
        "label":    label,
        "color":    color,
    }


def _score_article(article: dict) -> dict:
    """
    Score a single article using title-weighted + summary sentiment.

    Strategy:
    - Title carries 70% of the weight (short, punchy, most signal)
    - Summary carries 30% (often empty → graceful fallback)
    - If summary is empty, title score is used directly
    """
    title   = (article.get("title",   "") or "").strip()
    summary = (article.get("summary", "") or "").strip()

    title_scores   = analyze_sentiment(title)
    summary_scores = analyze_sentiment(summary) if summary else None

    if summary_scores:
        compound = round(
            0.70 * title_scores["compound"] +
            0.30 * summary_scores["compound"],
            4,
        )
        positive = round(0.70 * title_scores["positive"] + 0.30 * summary_scores["positive"], 4)
        negative = round(0.70 * title_scores["negative"] + 0.30 * summary_scores["negative"], 4)
        neutral  = round(0.70 * title_scores["neutral"]  + 0.30 * summary_scores["neutral"],  4)
    else:
        compound = title_scores["compound"]
        positive = title_scores["positive"]
        negative = title_scores["negative"]
        neutral  = title_scores["neutral"]

    if compound >= 0.05:
        label, color = "Positive", "success"
    elif compound <= -0.05:
        label, color = "Negative", "danger"
    else:
        label, color = "Neutral",  "warning"

    return {
        "compound": compound,
        "positive": positive,
        "negative": negative,
        "neutral":  neutral,
        "label":    label,
        "color":    color,
    }


# ── Public API ────────────────────────────────────────────────────────────────

def get_news_with_sentiment(ticker: str) -> list:
    """
    Fetch news for a ticker and attach sentiment scores to each article.
    Each article also gets a `recency_weight` field for downstream use.
    """
    news = fetch_news(ticker)
    if not news:
        return []

    results = []
    for article in news:
        sentiment = _score_article(article)
        weight    = _recency_weight(article.get("published", ""))
        results.append({
            **article,
            **sentiment,
            "recency_weight": round(weight, 4),
        })

    logger.info("Scored %d articles for %s", len(results), ticker)
    return results


def get_overall_sentiment(ticker: str) -> dict:
    """
    Compute an overall sentiment score across all recent news,
    weighted by article recency (recent articles count more).
    """
    news = get_news_with_sentiment(ticker)

    if not news:
        return {"label": "No Data", "color": "secondary", "compound": 0.0, "count": 0}

    total_weight    = sum(a["recency_weight"] for a in news)
    weighted_sum    = sum(a["compound"] * a["recency_weight"] for a in news)
    avg_compound    = round(weighted_sum / total_weight, 4) if total_weight else 0.0

    if avg_compound >= 0.05:
        label, color = "Overall Positive", "success"
    elif avg_compound <= -0.05:
        label, color = "Overall Negative", "danger"
    else:
        label, color = "Overall Neutral",  "warning"

    logger.info(
        "Overall sentiment for %s: %s (%.4f) across %d articles",
        ticker, label, avg_compound, len(news),
    )

    return {
        "label":    label,
        "color":    color,
        "compound": avg_compound,
        "count":    len(news),
    }