# data/indicators.py
import pandas as pd
import numpy as np


def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate Relative Strength Index (RSI)."""
    close = df["Close"]
    if isinstance(close.columns if hasattr(close, 'columns') else None, pd.MultiIndex):
        close = close.iloc[:, 0]
    
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9):
    """Calculate MACD, Signal line, and Histogram."""
    close = df["Close"]
    if hasattr(close, 'columns'):
        close = close.iloc[:, 0]

    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()

    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line

    return macd_line, signal_line, histogram


def calculate_bollinger_bands(df: pd.DataFrame, period: int = 20, std: int = 2):
    """Calculate Bollinger Bands."""
    close = df["Close"]
    if hasattr(close, 'columns'):
        close = close.iloc[:, 0]

    middle = close.rolling(window=period).mean()
    std_dev = close.rolling(window=period).std()

    upper = middle + (std_dev * std)
    lower = middle - (std_dev * std)

    return upper, middle, lower


def calculate_ema(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """Calculate Exponential Moving Average."""
    close = df["Close"]
    if hasattr(close, 'columns'):
        close = close.iloc[:, 0]
    return close.ewm(span=period, adjust=False).mean()


def calculate_sma(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """Calculate Simple Moving Average."""
    close = df["Close"]
    if hasattr(close, 'columns'):
        close = close.iloc[:, 0]
    return close.rolling(window=period).mean()


def get_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate all indicators and return enriched DataFrame."""
    result = df.copy()

    # Flatten MultiIndex columns if present
    if isinstance(result.columns, pd.MultiIndex):
        result.columns = result.columns.get_level_values(0)

    result["RSI"] = calculate_rsi(df)
    result["MACD"], result["MACD_Signal"], result["MACD_Hist"] = calculate_macd(df)
    result["BB_Upper"], result["BB_Middle"], result["BB_Lower"] = calculate_bollinger_bands(df)
    result["EMA_20"] = calculate_ema(df, 20)
    result["SMA_50"] = calculate_sma(df, 50)

    return result