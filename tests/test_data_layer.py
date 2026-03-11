# tests/test_data_layer.py
"""
Tests for data/indicators.py and data/sentiment.py

Run with:
    pytest tests/test_data_layer.py -v
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import pandas as pd
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta


# ── Shared fixture ────────────────────────────────────────────────────────────

def _make_df(n: int = 60) -> pd.DataFrame:
    """Generate a realistic OHLCV DataFrame with n rows."""
    np.random.seed(42)
    close  = 150 + np.cumsum(np.random.randn(n) * 0.5)
    high   = close + np.abs(np.random.randn(n) * 0.3)
    low    = close - np.abs(np.random.randn(n) * 0.3)
    open_  = close + np.random.randn(n) * 0.2
    volume = np.random.randint(1_000_000, 5_000_000, n).astype(float)

    return pd.DataFrame({
        "Open":   open_,
        "High":   high,
        "Low":    low,
        "Close":  close,
        "Volume": volume,
    }, index=pd.date_range("2024-01-01", periods=n, freq="D"))


DF = _make_df()


# ═══════════════════════════════════════════════════════════════════════════════
# indicators.py
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetCloseHelper:

    def test_flat_columns(self):
        from data.indicators import _get_close
        s = _get_close(DF)
        assert isinstance(s, pd.Series)
        assert len(s) == len(DF)

    def test_multiindex_columns(self):
        from data.indicators import _get_close
        mi = pd.MultiIndex.from_tuples([("Close", "AAPL"), ("Open", "AAPL")])
        df = pd.DataFrame(np.random.rand(10, 2), columns=mi)
        s  = _get_close(df)
        assert isinstance(s, pd.Series)


class TestCalculateRSI:

    def test_returns_series(self):
        from data.indicators import calculate_rsi
        rsi = calculate_rsi(DF)
        assert isinstance(rsi, pd.Series)

    def test_rsi_bounded_0_100(self):
        from data.indicators import calculate_rsi
        rsi = calculate_rsi(DF).dropna()
        assert (rsi >= 0).all() and (rsi <= 100).all()

    def test_rsi_length_matches_input(self):
        from data.indicators import calculate_rsi
        assert len(calculate_rsi(DF)) == len(DF)

    def test_rsi_empty_df_raises_or_returns_empty(self):
        from data.indicators import calculate_rsi
        try:
            result = calculate_rsi(pd.DataFrame(columns=["Close"]))
            assert result.empty or result.isna().all()
        except (KeyError, ValueError):
            pass   # acceptable — empty input


class TestCalculateMACD:

    def test_returns_three_series(self):
        from data.indicators import calculate_macd
        macd, signal, hist = calculate_macd(DF)
        assert all(isinstance(s, pd.Series) for s in (macd, signal, hist))

    def test_histogram_equals_macd_minus_signal(self):
        from data.indicators import calculate_macd
        macd, signal, hist = calculate_macd(DF)
        diff = (macd - signal - hist).dropna().abs()
        assert (diff < 1e-10).all()

    def test_lengths_match(self):
        from data.indicators import calculate_macd
        macd, signal, hist = calculate_macd(DF)
        assert len(macd) == len(signal) == len(hist) == len(DF)


class TestBollingerBands:

    def test_returns_three_series(self):
        from data.indicators import calculate_bollinger_bands
        upper, mid, lower = calculate_bollinger_bands(DF)
        assert all(isinstance(s, pd.Series) for s in (upper, mid, lower))

    def test_upper_above_lower(self):
        from data.indicators import calculate_bollinger_bands
        upper, _, lower = calculate_bollinger_bands(DF)
        valid = upper.dropna()
        lower_valid = lower.dropna()
        assert (valid.values >= lower_valid.values).all()

    def test_middle_between_bands(self):
        from data.indicators import calculate_bollinger_bands
        upper, mid, lower = calculate_bollinger_bands(DF)
        idx = upper.dropna().index
        assert (mid[idx] <= upper[idx]).all()
        assert (mid[idx] >= lower[idx]).all()


class TestATR:

    def test_returns_series(self):
        from data.indicators import calculate_atr
        atr = calculate_atr(DF)
        assert isinstance(atr, pd.Series)

    def test_atr_non_negative(self):
        from data.indicators import calculate_atr
        atr = calculate_atr(DF).dropna()
        assert (atr >= 0).all()

    def test_atr_length(self):
        from data.indicators import calculate_atr
        assert len(calculate_atr(DF)) == len(DF)


class TestVWAP:

    def test_returns_series(self):
        from data.indicators import calculate_vwap
        vwap = calculate_vwap(DF)
        assert isinstance(vwap, pd.Series)

    def test_vwap_positive(self):
        from data.indicators import calculate_vwap
        vwap = calculate_vwap(DF).dropna()
        assert (vwap > 0).all()

    def test_vwap_in_reasonable_range(self):
        from data.indicators import calculate_vwap
        vwap  = calculate_vwap(DF).dropna()
        close = DF["Close"]
        # VWAP should be in the ballpark of the price range
        assert vwap.min() > close.min() * 0.5
        assert vwap.max() < close.max() * 2.0


class TestGetAllIndicators:

    def test_adds_expected_columns(self):
        from data.indicators import get_all_indicators
        with patch("data.indicators._cache") as mock_cache:
            mock_cache.get.return_value = None
            mock_cache.set = MagicMock()
            result = get_all_indicators(DF)
            expected = ["RSI", "MACD", "MACD_Signal", "MACD_Hist",
                        "BB_Upper", "BB_Middle", "BB_Lower",
                        "EMA_20", "SMA_50", "ATR", "VWAP"]
            for col in expected:
                assert col in result.columns, f"Missing column: {col}"

    def test_returns_cached_result(self):
        from data.indicators import get_all_indicators
        fake = DF.copy()
        fake["RSI"] = 50.0
        with patch("data.indicators._cache") as mock_cache:
            mock_cache.get.return_value = fake
            result = get_all_indicators(DF)
            assert "RSI" in result.columns

    def test_empty_df_returns_early(self):
        from data.indicators import get_all_indicators
        result = get_all_indicators(pd.DataFrame())
        assert result.empty


# ═══════════════════════════════════════════════════════════════════════════════
# sentiment.py
# ═══════════════════════════════════════════════════════════════════════════════

def _make_mock_sia(compound: float = 0.5):
    """Return a mock SIA whose polarity_scores returns a fixed compound value."""
    mock_sia = MagicMock()
    mock_sia.polarity_scores.return_value = {
        "compound": compound, "pos": 0.4, "neg": 0.1, "neu": 0.5
    }
    return mock_sia


class TestAnalyzeSentiment:

    def test_positive_text(self):
        from data.sentiment import analyze_sentiment
        with patch("data.sentiment._get_sia", return_value=_make_mock_sia(0.6)):
            result = analyze_sentiment("Amazing record-breaking profits surge!")
            assert result["label"]    == "Positive"
            assert result["compound"] > 0.05

    def test_negative_text(self):
        from data.sentiment import analyze_sentiment
        with patch("data.sentiment._get_sia", return_value=_make_mock_sia(-0.6)):
            result = analyze_sentiment("Terrible crash losses collapse disaster")
            assert result["label"]    == "Negative"
            assert result["compound"] < -0.05

    def test_empty_string_returns_neutral(self):
        from data.sentiment import analyze_sentiment
        result = analyze_sentiment("")
        assert result["label"]    == "Neutral"
        assert result["compound"] == 0.0

    def test_returns_all_keys(self):
        from data.sentiment import analyze_sentiment
        with patch("data.sentiment._get_sia", return_value=_make_mock_sia(0.0)):
            result = analyze_sentiment("Stock market update today.")
            for key in ("compound", "positive", "negative", "neutral", "label", "color"):
                assert key in result

    def test_sia_is_singleton(self):
        """_get_sia is decorated with lru_cache — same object returned twice."""
        from data.sentiment import _get_sia
        with patch("data.sentiment.SentimentIntensityAnalyzer", return_value=MagicMock()) as mock_cls:
            _get_sia.cache_clear()
            sia1 = _get_sia()
            sia2 = _get_sia()
            assert sia1 is sia2
            mock_cls.assert_called_once()   # only instantiated once
            _get_sia.cache_clear()          # cleanup


class TestRecencyWeight:

    def test_recent_article_high_weight(self):
        from data.sentiment import _recency_weight
        now = datetime.now(tz=timezone.utc).isoformat()
        w   = _recency_weight(now)
        assert w > 0.9

    def test_old_article_low_weight(self):
        from data.sentiment import _recency_weight
        old = (datetime.now(tz=timezone.utc) - timedelta(days=7)).isoformat()
        w   = _recency_weight(old)
        assert w < 0.2

    def test_empty_string_returns_fallback(self):
        from data.sentiment import _recency_weight
        assert _recency_weight("") == 0.5

    def test_invalid_date_returns_fallback(self):
        from data.sentiment import _recency_weight
        assert _recency_weight("not-a-date") == 0.5

    def test_unix_timestamp_string(self):
        from data.sentiment import _recency_weight
        import time
        ts = str(int(time.time()))
        w  = _recency_weight(ts)
        assert w > 0.9


class TestGetNewsWithSentiment:

    def _mock_news(self):
        return [
            {
                "title":     "Apple hits all-time high",
                "summary":   "Record profits reported today.",
                "url":       "https://example.com/1",
                "publisher": "Reuters",
                "published": datetime.now(tz=timezone.utc).isoformat(),
            },
            {
                "title":     "Market crash fears grow",
                "summary":   "",
                "url":       "https://example.com/2",
                "publisher": "Bloomberg",
                "published": (datetime.now(tz=timezone.utc) - timedelta(hours=2)).isoformat(),
            },
        ]

    def test_returns_list_with_sentiment_keys(self):
        from data.sentiment import get_news_with_sentiment
        with patch("data.sentiment.fetch_news", return_value=self._mock_news()), \
             patch("data.sentiment._get_sia", return_value=_make_mock_sia(0.4)):
            results = get_news_with_sentiment("AAPL")
            assert len(results) == 2
            for r in results:
                assert "compound"       in r
                assert "label"          in r
                assert "recency_weight" in r

    def test_empty_news_returns_empty_list(self):
        from data.sentiment import get_news_with_sentiment
        with patch("data.sentiment.fetch_news", return_value=[]):
            assert get_news_with_sentiment("AAPL") == []

    def test_recency_weight_present_and_valid(self):
        from data.sentiment import get_news_with_sentiment
        with patch("data.sentiment.fetch_news", return_value=self._mock_news()), \
             patch("data.sentiment._get_sia", return_value=_make_mock_sia(0.3)):
            results = get_news_with_sentiment("AAPL")
            for r in results:
                assert 0.0 < r["recency_weight"] <= 1.0


class TestGetOverallSentiment:

    def _mock_scored(self, compounds, hours_ago_list):
        from datetime import datetime, timezone, timedelta
        articles = []
        for c, h in zip(compounds, hours_ago_list):
            pub = (datetime.now(tz=timezone.utc) - timedelta(hours=h)).isoformat()
            label = "Positive" if c >= 0.05 else ("Negative" if c <= -0.05 else "Neutral")
            articles.append({
                "title": "x", "summary": "", "url": "#",
                "publisher": "X", "published": pub,
                "compound": c, "positive": 0, "negative": 0, "neutral": 1,
                "label": label, "color": "success",
                "recency_weight": 1.0,
            })
        return articles

    def test_returns_expected_keys(self):
        from data.sentiment import get_overall_sentiment
        with patch("data.sentiment.get_news_with_sentiment",
                   return_value=self._mock_scored([0.3, 0.2], [1, 2])):
            result = get_overall_sentiment("AAPL")
            for key in ("label", "color", "compound", "count"):
                assert key in result

    def test_no_news_returns_no_data(self):
        from data.sentiment import get_overall_sentiment
        with patch("data.sentiment.get_news_with_sentiment", return_value=[]):
            result = get_overall_sentiment("AAPL")
            assert result["label"] == "No Data"

    def test_recent_articles_weighted_more(self):
        """A recent positive article should outweigh an older negative one."""
        from data.sentiment import get_overall_sentiment
        articles = self._mock_scored(
            compounds   = [0.8,  -0.8],
            hours_ago_list = [0.1,  72],    # one just now, one 3 days ago
        )
        # Manually set recency weights to reflect the difference
        articles[0]["recency_weight"] = 0.99
        articles[1]["recency_weight"] = 0.06
        with patch("data.sentiment.get_news_with_sentiment", return_value=articles):
            result = get_overall_sentiment("AAPL")
            assert result["compound"] > 0, "Recent positive should dominate"