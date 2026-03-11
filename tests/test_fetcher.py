# tests/test_fetcher.py
"""
Tests for data/fetcher.py

Run with:
    pytest tests/ -v
"""

import asyncio
import pandas as pd
import pytest
from unittest.mock import patch, MagicMock

# ── We import after patching so diskcache doesn't write during tests ──────────
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── Fixtures ──────────────────────────────────────────────────────────────────

MOCK_OHLCV = pd.DataFrame({
    "Open":   [150.0, 152.0],
    "High":   [155.0, 156.0],
    "Low":    [149.0, 151.0],
    "Close":  [153.0, 154.0],
    "Volume": [1000000, 1200000],
}, index=pd.to_datetime(["2024-01-01", "2024-01-02"]))

MOCK_INFO = {
    "longName":          "Apple Inc.",
    "sector":            "Technology",
    "marketCap":         3_000_000_000_000,
    "trailingPE":        29.5,
    "currentPrice":      195.0,
    "fiftyTwoWeekHigh":  200.0,
    "fiftyTwoWeekLow":   140.0,
    "currency":          "USD",
}

MOCK_NEWS = [
    {
        "content": {
            "title":        "Apple hits record high",
            "summary":      "Apple stock surged today...",
            "pubDate":      "2024-06-01T10:00:00Z",
            "canonicalUrl": {"url": "https://example.com/apple"},
            "provider":     {"displayName": "Reuters"},
        }
    }
]


# ── fetch_stock_data ──────────────────────────────────────────────────────────

class TestFetchStockData:

    def test_returns_dataframe_on_success(self):
        with patch("data.fetcher._cache") as mock_cache, \
             patch("yfinance.download", return_value=MOCK_OHLCV):
            mock_cache.get.return_value = None
            mock_cache.set = MagicMock()
            from data.fetcher import fetch_stock_data
            df = fetch_stock_data("AAPL", "6mo")
            assert isinstance(df, pd.DataFrame)
            assert not df.empty
            assert list(df.columns) == ["Open", "High", "Low", "Close", "Volume"]

    def test_returns_empty_df_on_yfinance_error(self):
        with patch("data.fetcher._cache") as mock_cache, \
             patch("yfinance.download", side_effect=Exception("network error")):
            mock_cache.get.return_value = None
            from data.fetcher import fetch_stock_data
            df = fetch_stock_data("INVALID", "6mo")
            assert isinstance(df, pd.DataFrame)
            assert df.empty

    def test_returns_cached_value_without_network_call(self):
        with patch("data.fetcher._cache") as mock_cache, \
             patch("yfinance.download") as mock_yf:
            mock_cache.get.return_value = MOCK_OHLCV
            from data.fetcher import fetch_stock_data
            df = fetch_stock_data("AAPL", "6mo")
            mock_yf.assert_not_called()
            assert df is MOCK_OHLCV

    def test_invalid_period_falls_back_to_6mo(self):
        with patch("data.fetcher._cache") as mock_cache, \
             patch("yfinance.download", return_value=MOCK_OHLCV) as mock_yf:
            mock_cache.get.return_value = None
            mock_cache.set = MagicMock()
            from data.fetcher import fetch_stock_data
            fetch_stock_data("AAPL", "INVALID")
            call_kwargs = mock_yf.call_args
            assert call_kwargs.kwargs.get("period") == "6mo" or \
                   call_kwargs.args[1] == "6mo" if call_kwargs.args else True


# ── fetch_stock_info ──────────────────────────────────────────────────────────

class TestFetchStockInfo:

    def _mock_ticker(self):
        mock_t = MagicMock()
        mock_t.info = MOCK_INFO
        return mock_t

    def test_returns_complete_info_dict(self):
        with patch("data.fetcher._cache") as mock_cache, \
             patch("yfinance.Ticker", return_value=self._mock_ticker()):
            mock_cache.get.return_value = None
            mock_cache.set = MagicMock()
            from data.fetcher import fetch_stock_info
            info = fetch_stock_info("AAPL")
            assert info["name"]          == "Apple Inc."
            assert info["sector"]        == "Technology"
            assert info["market_cap"]    == 3_000_000_000_000
            assert info["current_price"] == 195.0
            assert info["currency"]      == "USD"

    def test_returns_empty_dict_on_error(self):
        with patch("data.fetcher._cache") as mock_cache, \
             patch("yfinance.Ticker", side_effect=Exception("API error")):
            mock_cache.get.return_value = None
            from data.fetcher import fetch_stock_info
            result = fetch_stock_info("INVALID")
            assert result == {}

    def test_missing_fields_default_to_zero_or_na(self):
        with patch("data.fetcher._cache") as mock_cache, \
             patch("yfinance.Ticker") as mock_yf:
            mock_cache.get.return_value = None
            mock_cache.set = MagicMock()
            mock_t = MagicMock()
            mock_t.info = {"longName": "Test Corp"}   # minimal info
            mock_yf.return_value = mock_t
            from data.fetcher import fetch_stock_info
            info = fetch_stock_info("TEST")
            assert info["market_cap"]    == 0.0
            assert info["pe_ratio"]      == 0.0
            assert info["current_price"] == 0.0
            assert info["sector"]        == "N/A"


# ── fetch_news ────────────────────────────────────────────────────────────────

class TestFetchNews:

    def test_returns_list_of_articles(self):
        with patch("data.fetcher._cache") as mock_cache, \
             patch("yfinance.Ticker") as mock_yf:
            mock_cache.get.return_value = None
            mock_cache.set = MagicMock()
            mock_t = MagicMock()
            mock_t.news = MOCK_NEWS
            mock_yf.return_value = mock_t
            from data.fetcher import fetch_news
            news = fetch_news("AAPL")
            assert isinstance(news, list)
            assert len(news) == 1
            assert news[0]["title"] == "Apple hits record high"
            assert news[0]["publisher"] == "Reuters"

    def test_returns_empty_list_on_error(self):
        with patch("data.fetcher._cache") as mock_cache, \
             patch("yfinance.Ticker", side_effect=Exception("error")):
            mock_cache.get.return_value = None
            from data.fetcher import fetch_news
            result = fetch_news("INVALID")
            assert result == []

    def test_returns_empty_list_when_no_news(self):
        with patch("data.fetcher._cache") as mock_cache, \
             patch("yfinance.Ticker") as mock_yf:
            mock_cache.get.return_value = None
            mock_cache.set = MagicMock()
            mock_t = MagicMock()
            mock_t.news = []
            mock_yf.return_value = mock_t
            from data.fetcher import fetch_news
            result = fetch_news("AAPL")
            assert result == []


# ── get_current_price ─────────────────────────────────────────────────────────

class TestGetCurrentPrice:

    def test_returns_float_from_ohlcv(self):
        with patch("data.fetcher.fetch_stock_data", return_value=MOCK_OHLCV):
            from data.fetcher import get_current_price
            price = get_current_price("AAPL")
            assert isinstance(price, float)
            assert price == 154.0

    def test_falls_back_to_info_when_ohlcv_empty(self):
        with patch("data.fetcher.fetch_stock_data", return_value=pd.DataFrame()), \
             patch("data.fetcher.fetch_stock_info", return_value={"current_price": 195.0}):
            from data.fetcher import get_current_price
            price = get_current_price("AAPL")
            assert price == 195.0

    def test_returns_zero_on_total_failure(self):
        with patch("data.fetcher.fetch_stock_data", side_effect=Exception("fail")):
            from data.fetcher import get_current_price
            price = get_current_price("INVALID")
            assert price == 0.0


# ── fetch_many (async) ────────────────────────────────────────────────────────

class TestFetchMany:

    def test_fetches_multiple_tickers(self):
        def mock_fetch(ticker, period):
            return MOCK_OHLCV

        with patch("data.fetcher.fetch_stock_data", side_effect=mock_fetch):
            from data.fetcher import fetch_many
            results = fetch_many(["AAPL", "TSLA", "NVDA"])
            assert set(results.keys()) == {"AAPL", "TSLA", "NVDA"}
            for df in results.values():
                assert not df.empty


# ── utils/helpers ─────────────────────────────────────────────────────────────

class TestHelpers:

    def test_fmt_market_cap_trillions(self):
        from utils.helpers import fmt_market_cap
        assert fmt_market_cap(3e12) == "$3.00T"

    def test_fmt_market_cap_billions(self):
        from utils.helpers import fmt_market_cap
        assert fmt_market_cap(500e9) == "$500.00B"

    def test_fmt_market_cap_none(self):
        from utils.helpers import fmt_market_cap
        assert fmt_market_cap(0) == "N/A"

    def test_currency_symbol_inr(self):
        from utils.helpers import currency_symbol
        assert currency_symbol("INR") == "₹"

    def test_currency_symbol_default(self):
        from utils.helpers import currency_symbol
        assert currency_symbol("USD") == "$"

    def test_safe_round_normal(self):
        from utils.helpers import safe_round
        assert safe_round(3.14159) == 3.14

    def test_safe_round_none(self):
        from utils.helpers import safe_round
        assert safe_round(None) == 0.0

    def test_retry_succeeds_after_failures(self):
        from utils.helpers import retry
        call_count = {"n": 0}

        @retry(max_attempts=3, delay=0)
        def flaky():
            call_count["n"] += 1
            if call_count["n"] < 3:
                raise ValueError("not yet")
            return "ok"

        assert flaky() == "ok"
        assert call_count["n"] == 3

    def test_retry_raises_after_max_attempts(self):
        from utils.helpers import retry

        @retry(max_attempts=2, delay=0)
        def always_fails():
            raise RuntimeError("always")

        with pytest.raises(RuntimeError):
            always_fails()