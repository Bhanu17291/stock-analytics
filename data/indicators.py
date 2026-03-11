# data/indicators.py
import logging
import hashlib

import numpy as np
import pandas as pd
import diskcache

logger = logging.getLogger(__name__)

_cache = diskcache.Cache(".cache/indicators")
CACHE_TTL = 60 * 15   # 15 minutes — same as OHLCV


# ── Internal helpers ──────────────────────────────────────────────────────────

def _get_close(df: pd.DataFrame) -> pd.Series:
    """
    Safely extract the Close series from a DataFrame,
    handling both flat and MultiIndex columns.
    """
    close = df["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    return close.astype(float)


def _df_hash(df: pd.DataFrame) -> str:
    """Produce a short cache key from a DataFrame's shape + last index value."""
    last_idx = str(df.index[-1]) if len(df) else "empty"
    return hashlib.md5(f"{df.shape}{last_idx}".encode()).hexdigest()[:12]


# ── Individual Indicators ─────────────────────────────────────────────────────

def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Relative Strength Index (RSI) using Wilder's smoothing (EWM)."""
    close = _get_close(df)
    delta = close.diff()
    gain  = delta.where(delta > 0, 0.0)
    loss  = -delta.where(delta < 0, 0.0)

    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()

    # Avoid division by zero
    rs  = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.rename("RSI")


def calculate_macd(
    df: pd.DataFrame,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """MACD line, Signal line, and Histogram."""
    close      = _get_close(df)
    ema_fast   = close.ewm(span=fast,   adjust=False).mean()
    ema_slow   = close.ewm(span=slow,   adjust=False).mean()
    macd_line  = ema_fast - ema_slow
    signal_line= macd_line.ewm(span=signal, adjust=False).mean()
    histogram  = macd_line - signal_line
    return (
        macd_line.rename("MACD"),
        signal_line.rename("MACD_Signal"),
        histogram.rename("MACD_Hist"),
    )


def calculate_bollinger_bands(
    df: pd.DataFrame,
    period: int = 20,
    std: int = 2,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Upper, Middle (SMA), and Lower Bollinger Bands."""
    close   = _get_close(df)
    middle  = close.rolling(window=period).mean()
    std_dev = close.rolling(window=period).std()
    upper   = middle + std_dev * std
    lower   = middle - std_dev * std
    return (
        upper.rename("BB_Upper"),
        middle.rename("BB_Middle"),
        lower.rename("BB_Lower"),
    )


def calculate_ema(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """Exponential Moving Average."""
    return _get_close(df).ewm(span=period, adjust=False).mean().rename(f"EMA_{period}")


def calculate_sma(df: pd.DataFrame, period: int = 50) -> pd.Series:
    """Simple Moving Average."""
    return _get_close(df).rolling(window=period).mean().rename(f"SMA_{period}")


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Average True Range (ATR) — measures market volatility.
    True Range = max(High-Low, |High-PrevClose|, |Low-PrevClose|)
    """
    high  = df["High"].astype(float)
    low   = df["Low"].astype(float)
    close = _get_close(df)

    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low  - prev_close).abs(),
    ], axis=1).max(axis=1)

    atr = tr.ewm(com=period - 1, min_periods=period).mean()
    return atr.rename("ATR")


def calculate_vwap(df: pd.DataFrame) -> pd.Series:
    """
    Volume Weighted Average Price (VWAP).
    Uses typical price: (High + Low + Close) / 3.
    Resets daily (each row is treated as one trading day).
    """
    typical = (df["High"].astype(float) +
               df["Low"].astype(float)  +
               _get_close(df)) / 3
    volume  = df["Volume"].astype(float)

    cum_tp_vol = (typical * volume).cumsum()
    cum_vol    = volume.cumsum()

    vwap = cum_tp_vol / cum_vol.replace(0, np.nan)
    return vwap.rename("VWAP")


# ── Master function ───────────────────────────────────────────────────────────

def get_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute all indicators and return an enriched DataFrame.
    Results are cached by DataFrame fingerprint for 15 minutes.
    """
    if df.empty:
        logger.warning("get_all_indicators received an empty DataFrame")
        return df

    cache_key = f"indicators:{_df_hash(df)}"
    cached    = _cache.get(cache_key)
    if cached is not None:
        logger.debug("Cache hit for indicators (key=%s)", cache_key)
        return cached

    logger.info("Computing indicators for DataFrame with %d rows", len(df))

    result = df.copy()

    # Flatten MultiIndex columns if yfinance returned them
    if isinstance(result.columns, pd.MultiIndex):
        result.columns = result.columns.get_level_values(0)

    try:
        result["RSI"]                                         = calculate_rsi(df)
        result["MACD"], result["MACD_Signal"], result["MACD_Hist"] = calculate_macd(df)
        result["BB_Upper"], result["BB_Middle"], result["BB_Lower"] = calculate_bollinger_bands(df)
        result["EMA_20"] = calculate_ema(df, 20)
        result["SMA_50"] = calculate_sma(df, 50)
        result["ATR"]    = calculate_atr(df)
        result["VWAP"]   = calculate_vwap(df)
    except KeyError as e:
        logger.error("Missing expected column while computing indicators: %s", e)
    except Exception:
        logger.exception("Unexpected error computing indicators")

    _cache.set(cache_key, result, expire=CACHE_TTL)
    return result