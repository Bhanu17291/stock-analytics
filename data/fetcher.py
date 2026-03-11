# data/fetcher.py
import asyncio
import logging
import time
from typing import Optional

import httpx
import pandas as pd
import yfinance as yf
import diskcache
from pydantic import BaseModel, Field, field_validator

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── Cache (disk-backed, survives restarts) ────────────────────────────────────
_cache = diskcache.Cache(".cache/stock_data")

CACHE_TTL_PRICE  = 60 * 15       # 15 minutes  — price / OHLCV
CACHE_TTL_INFO   = 60 * 60       # 1 hour      — stock metadata
CACHE_TTL_NEWS   = 60 * 30       # 30 minutes  — news articles

# ── Pydantic Models ───────────────────────────────────────────────────────────

class StockInfo(BaseModel):
    ticker:        str
    name:          str       = "N/A"
    sector:        str       = "N/A"
    market_cap:    float     = 0.0
    pe_ratio:      float     = 0.0
    current_price: float     = 0.0
    week_52_high:  float     = Field(0.0, alias="52w_high")
    week_52_low:   float     = Field(0.0, alias="52w_low")
    currency:      str       = "USD"

    model_config = {"populate_by_name": True}

    @field_validator("market_cap", "pe_ratio", "current_price",
                     "week_52_high", "week_52_low", mode="before")
    @classmethod
    def coerce_none_to_zero(cls, v):
        return v if v is not None else 0.0


class NewsItem(BaseModel):
    title:     str = "No title"
    summary:   str = ""
    url:       str = "#"
    publisher: str = "Unknown"
    published: str = ""


# ── Core Fetch Functions ──────────────────────────────────────────────────────

def fetch_stock_data(ticker: str, period: str = "6mo") -> pd.DataFrame:
    """
    Fetch OHLCV data for a ticker using yfinance.
    Results are cached for CACHE_TTL_PRICE seconds.
    """
    cache_key = f"ohlcv:{ticker}:{period}"
    cached = _cache.get(cache_key)
    if cached is not None:
        logger.debug("Cache hit for OHLCV %s [%s]", ticker, period)
        return cached

    valid_periods = {"1mo", "3mo", "6mo", "1y", "2y", "5y"}
    if period not in valid_periods:
        logger.warning("Invalid period '%s', falling back to '6mo'", period)
        period = "6mo"

    try:
        logger.info("Fetching OHLCV data: %s [%s]", ticker, period)
        df = yf.download(ticker, period=period, interval="1d", progress=False, auto_adjust=True)

        if df.empty:
            logger.warning("No OHLCV data returned for %s", ticker)
            return pd.DataFrame()

        # Flatten MultiIndex columns (yfinance sometimes returns them)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df.index = pd.to_datetime(df.index).tz_localize(None)
        df = df.dropna()

        _cache.set(cache_key, df, expire=CACHE_TTL_PRICE)
        logger.info("Fetched %d rows for %s", len(df), ticker)
        return df

    except Exception:
        logger.exception("Failed to fetch OHLCV data for %s", ticker)
        return pd.DataFrame()


def fetch_stock_info(ticker: str) -> dict:
    """
    Fetch stock metadata (name, sector, market cap, P/E, etc.) using yfinance.
    Results are cached for CACHE_TTL_INFO seconds.
    Returns a plain dict for backward compatibility with app.py.
    """
    cache_key = f"info:{ticker}"
    cached = _cache.get(cache_key)
    if cached is not None:
        logger.debug("Cache hit for info %s", ticker)
        return cached

    try:
        logger.info("Fetching stock info: %s", ticker)
        t    = yf.Ticker(ticker)
        meta = t.info or {}

        info = StockInfo(
            ticker        = ticker,
            name          = meta.get("longName") or meta.get("shortName") or ticker,
            sector        = meta.get("sector") or "N/A",
            market_cap    = meta.get("marketCap") or 0.0,
            pe_ratio      = meta.get("trailingPE") or 0.0,
            current_price = meta.get("currentPrice") or meta.get("regularMarketPrice") or 0.0,
            **{"52w_high": meta.get("fiftyTwoWeekHigh") or 0.0,
               "52w_low":  meta.get("fiftyTwoWeekLow")  or 0.0},
            currency      = meta.get("currency") or "USD",
        )

        result = info.model_dump(by_alias=True)
        _cache.set(cache_key, result, expire=CACHE_TTL_INFO)
        return result

    except Exception:
        logger.exception("Failed to fetch stock info for %s", ticker)
        return {}


def fetch_news(ticker: str) -> list:
    """
    Fetch recent news articles for a ticker using yfinance.
    Results are cached for CACHE_TTL_NEWS seconds.
    Returns a list of plain dicts for backward compatibility.
    """
    cache_key = f"news:{ticker}"
    cached = _cache.get(cache_key)
    if cached is not None:
        logger.debug("Cache hit for news %s", ticker)
        return cached

    try:
        logger.info("Fetching news: %s", ticker)
        t    = yf.Ticker(ticker)
        raw  = t.news or []

        results = []
        for item in raw[:10]:
            content   = item.get("content", {})
            pub_time  = content.get("pubDate", "")

            article = NewsItem(
                title     = content.get("title") or item.get("title") or "No title",
                summary   = content.get("summary") or "",
                url       = (content.get("canonicalUrl", {}) or {}).get("url")
                            or item.get("link") or "#",
                publisher = (content.get("provider", {}) or {}).get("displayName")
                            or item.get("publisher") or "Unknown",
                published = str(pub_time),
            )
            results.append(article.model_dump())

        _cache.set(cache_key, results, expire=CACHE_TTL_NEWS)
        logger.info("Fetched %d news articles for %s", len(results), ticker)
        return results

    except Exception:
        logger.exception("Failed to fetch news for %s", ticker)
        return []


def get_current_price(ticker: str) -> float:
    """Return the latest closing price for a ticker."""
    try:
        df = fetch_stock_data(ticker, period="5d")
        if not df.empty:
            return round(float(df["Close"].iloc[-1]), 2)
        # Fallback: pull from info
        info = fetch_stock_info(ticker)
        return round(float(info.get("current_price", 0.0)), 2)
    except Exception:
        logger.exception("Failed to get current price for %s", ticker)
        return 0.0


# ── Async Multi-Ticker Fetch ──────────────────────────────────────────────────

async def _fetch_one_async(ticker: str, period: str) -> tuple[str, pd.DataFrame]:
    """Fetch OHLCV for a single ticker asynchronously (runs yfinance in thread pool)."""
    loop = pd.DataFrame()
    try:
        loop = await asyncio.get_event_loop().run_in_executor(
            None, fetch_stock_data, ticker, period
        )
    except Exception:
        logger.exception("Async fetch failed for %s", ticker)
    return ticker, loop


async def fetch_many_async(tickers: list[str], period: str = "6mo") -> dict[str, pd.DataFrame]:
    """
    Fetch OHLCV data for multiple tickers concurrently.

    Usage:
        results = asyncio.run(fetch_many_async(["AAPL", "TSLA", "NVDA"]))
    """
    logger.info("Fetching %d tickers concurrently: %s", len(tickers), tickers)
    tasks   = [_fetch_one_async(t, period) for t in tickers]
    results = await asyncio.gather(*tasks)
    return dict(results)


def fetch_many(tickers: list[str], period: str = "6mo") -> dict[str, pd.DataFrame]:
    """Synchronous wrapper around fetch_many_async — safe to call anywhere."""
    return asyncio.run(fetch_many_async(tickers, period))


# ── Cache Utilities ───────────────────────────────────────────────────────────

def clear_cache(ticker: str | None = None) -> None:
    """Clear cache for a specific ticker, or the entire cache if ticker is None."""
    if ticker:
        for prefix in ("ohlcv", "info", "news"):
            for key in list(_cache):
                if key.startswith(f"{prefix}:{ticker}"):
                    del _cache[key]
        logger.info("Cache cleared for %s", ticker)
    else:
        _cache.clear()
        logger.info("Entire cache cleared")