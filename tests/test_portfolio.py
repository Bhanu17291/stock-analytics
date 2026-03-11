# tests/test_portfolio.py
"""
Tests for components/portfolio.py

Run with:
    pytest tests/test_portfolio.py -v
"""

import json
import os
import sys
import tempfile
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── Helpers ───────────────────────────────────────────────────────────────────

def _write_json(path: str, data: dict):
    with open(path, "w") as f:
        json.dump(data, f)


SAMPLE_PORTFOLIO = {
    "AAPL": {"shares": 10.0, "buy_price": 150.0, "added_at": "2024-01-01T00:00:00"},
    "TSLA": {"shares": 5.0,  "buy_price": 200.0, "added_at": "2024-01-02T00:00:00"},
}


# ═══════════════════════════════════════════════════════════════════════════════
# _safe_load / _safe_save
# ═══════════════════════════════════════════════════════════════════════════════

class TestSafeLoad:

    def test_returns_default_when_file_missing(self, tmp_path):
        from components.portfolio import _safe_load
        result = _safe_load(str(tmp_path / "missing.json"), {})
        assert result == {}

    def test_loads_valid_json(self, tmp_path):
        from components.portfolio import _safe_load
        p = tmp_path / "data.json"
        _write_json(str(p), {"key": "value"})
        assert _safe_load(str(p), {}) == {"key": "value"}

    def test_returns_default_on_corrupt_json(self, tmp_path):
        from components.portfolio import _safe_load
        p = tmp_path / "corrupt.json"
        p.write_text("{ not valid json !!!")
        result = _safe_load(str(p), {"fallback": True})
        assert result == {"fallback": True}

    def test_restores_from_backup_on_corrupt(self, tmp_path):
        from components.portfolio import _safe_load
        p   = tmp_path / "data.json"
        bak = tmp_path / "data.json.bak"
        p.write_text("CORRUPT")
        _write_json(str(bak), {"restored": True})
        result = _safe_load(str(p), {})
        assert result == {"restored": True}


class TestSafeSave:

    def test_saves_json(self, tmp_path):
        from components.portfolio import _safe_save
        p = str(tmp_path / "out.json")
        _safe_save(p, {"a": 1})
        with open(p) as f:
            assert json.load(f) == {"a": 1}

    def test_creates_backup_of_previous(self, tmp_path):
        from components.portfolio import _safe_save
        p = str(tmp_path / "out.json")
        _safe_save(p, {"v": 1})
        _safe_save(p, {"v": 2})
        with open(p + ".bak") as f:
            assert json.load(f) == {"v": 1}


# ═══════════════════════════════════════════════════════════════════════════════
# _validate
# ═══════════════════════════════════════════════════════════════════════════════

class TestValidate:

    def test_valid_inputs_pass(self):
        from components.portfolio import _validate
        _validate("AAPL", 10.0, 150.0)   # should not raise

    def test_empty_ticker_raises(self):
        from components.portfolio import _validate
        with pytest.raises(ValueError, match="empty"):
            _validate("", 10.0, 150.0)

    def test_zero_shares_raises(self):
        from components.portfolio import _validate
        with pytest.raises(ValueError, match="Shares"):
            _validate("AAPL", 0, 150.0)

    def test_negative_shares_raises(self):
        from components.portfolio import _validate
        with pytest.raises(ValueError, match="Shares"):
            _validate("AAPL", -5, 150.0)

    def test_zero_buy_price_raises(self):
        from components.portfolio import _validate
        with pytest.raises(ValueError, match="Buy price"):
            _validate("AAPL", 10.0, 0)

    def test_negative_buy_price_raises(self):
        from components.portfolio import _validate
        with pytest.raises(ValueError, match="Buy price"):
            _validate("AAPL", 10.0, -1)


# ═══════════════════════════════════════════════════════════════════════════════
# add_stock / remove_stock
# ═══════════════════════════════════════════════════════════════════════════════

class TestAddRemoveStock:

    def test_add_stock_saves_correctly(self, tmp_path):
        from components import portfolio as pm
        with patch.object(pm, "PORTFOLIO_FILE", str(tmp_path / "p.json")):
            result = pm.add_stock("AAPL", 10.0, 150.0)
            assert "AAPL" in result
            assert result["AAPL"]["shares"]    == 10.0
            assert result["AAPL"]["buy_price"] == 150.0

    def test_add_stock_uppercases_ticker(self, tmp_path):
        from components import portfolio as pm
        with patch.object(pm, "PORTFOLIO_FILE", str(tmp_path / "p.json")):
            result = pm.add_stock("aapl", 5.0, 100.0)
            assert "AAPL" in result

    def test_add_stock_invalid_raises(self, tmp_path):
        from components import portfolio as pm
        with patch.object(pm, "PORTFOLIO_FILE", str(tmp_path / "p.json")):
            with pytest.raises(ValueError):
                pm.add_stock("AAPL", -1, 100.0)

    def test_remove_stock_deletes_entry(self, tmp_path):
        from components import portfolio as pm
        pf = str(tmp_path / "p.json")
        _write_json(pf, SAMPLE_PORTFOLIO)
        with patch.object(pm, "PORTFOLIO_FILE", pf):
            result = pm.remove_stock("AAPL")
            assert "AAPL" not in result
            assert "TSLA" in result

    def test_remove_nonexistent_stock_is_silent(self, tmp_path):
        from components import portfolio as pm
        pf = str(tmp_path / "p.json")
        _write_json(pf, {})
        with patch.object(pm, "PORTFOLIO_FILE", pf):
            result = pm.remove_stock("NVDA")
            assert result == {}


# ═══════════════════════════════════════════════════════════════════════════════
# get_portfolio_summary
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetPortfolioSummary:

    def _mock_prices(self):
        import pandas as pd
        df = pd.DataFrame({"Close": [200.0]}, index=pd.to_datetime(["2024-06-01"]))
        return {"AAPL": df, "TSLA": df}

    def test_returns_correct_pnl(self, tmp_path):
        from components import portfolio as pm
        pf = str(tmp_path / "p.json")
        _write_json(pf, {
            "AAPL": {"shares": 10.0, "buy_price": 150.0, "added_at": ""},
        })
        with patch.object(pm, "PORTFOLIO_FILE", pf), \
             patch("components.portfolio.fetch_many", return_value=self._mock_prices()):
            summary = pm.get_portfolio_summary()
            assert len(summary) == 1
            item = summary[0]
            assert item["ticker"]        == "AAPL"
            assert item["current_price"] == 200.0
            assert item["invested"]      == 1500.0
            assert item["current_value"] == 2000.0
            assert item["pnl"]           == 500.0
            assert item["color"]         == "success"

    def test_returns_empty_for_empty_portfolio(self, tmp_path):
        from components import portfolio as pm
        pf = str(tmp_path / "p.json")
        _write_json(pf, {})
        with patch.object(pm, "PORTFOLIO_FILE", pf):
            assert pm.get_portfolio_summary() == []

    def test_negative_pnl_shows_danger(self, tmp_path):
        import pandas as pd
        from components import portfolio as pm
        pf = str(tmp_path / "p.json")
        _write_json(pf, {
            "AAPL": {"shares": 10.0, "buy_price": 200.0, "added_at": ""},
        })
        low_df = pd.DataFrame({"Close": [100.0]}, index=pd.to_datetime(["2024-06-01"]))
        with patch.object(pm, "PORTFOLIO_FILE", pf), \
             patch("components.portfolio.fetch_many", return_value={"AAPL": low_df}):
            summary = pm.get_portfolio_summary()
            assert summary[0]["pnl"]   < 0
            assert summary[0]["color"] == "danger"


# ═══════════════════════════════════════════════════════════════════════════════
# get_portfolio_totals
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetPortfolioTotals:

    def test_totals_sum_correctly(self, tmp_path):
        import pandas as pd
        from components import portfolio as pm
        pf = str(tmp_path / "p.json")
        _write_json(pf, {
            "AAPL": {"shares": 10.0, "buy_price": 100.0, "added_at": ""},
            "TSLA": {"shares":  5.0, "buy_price": 200.0, "added_at": ""},
        })
        df200 = pd.DataFrame({"Close": [200.0]}, index=pd.to_datetime(["2024-06-01"]))
        df300 = pd.DataFrame({"Close": [300.0]}, index=pd.to_datetime(["2024-06-01"]))
        with patch.object(pm, "PORTFOLIO_FILE", pf), \
             patch("components.portfolio.fetch_many", return_value={"AAPL": df200, "TSLA": df300}):
            totals = pm.get_portfolio_totals()
            assert totals["invested"]      == 2000.0
            assert totals["current_value"] == 3500.0
            assert totals["pnl"]           == 1500.0

    def test_returns_zeros_for_empty_portfolio(self, tmp_path):
        from components import portfolio as pm
        pf = str(tmp_path / "p.json")
        _write_json(pf, {})
        with patch.object(pm, "PORTFOLIO_FILE", pf):
            totals = pm.get_portfolio_totals()
            assert totals["invested"]      == 0.0
            assert totals["current_value"] == 0.0
            assert totals["pnl"]           == 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# history snapshots
# ═══════════════════════════════════════════════════════════════════════════════

class TestPortfolioHistory:

    def test_snapshot_saves_today(self, tmp_path):
        from components import portfolio as pm
        from datetime import date
        hf = str(tmp_path / "history.json")
        mock_totals = {"invested": 1000.0, "current_value": 1200.0, "pnl": 200.0, "pnl_pct": 20.0}
        with patch.object(pm, "HISTORY_FILE", hf), \
             patch("components.portfolio.get_portfolio_totals", return_value=mock_totals):
            pm.record_portfolio_snapshot()
            history = json.load(open(hf))
            today   = date.today().isoformat()
            assert today in history
            assert history[today]["current_value"] == 1200.0

    def test_get_portfolio_history_sorted(self, tmp_path):
        from components import portfolio as pm
        hf = str(tmp_path / "history.json")
        _write_json(hf, {
            "2024-03-01": {"invested": 1000, "current_value": 1100, "pnl": 100, "pnl_pct": 10},
            "2024-01-01": {"invested": 900,  "current_value": 950,  "pnl": 50,  "pnl_pct": 5},
            "2024-02-01": {"invested": 950,  "current_value": 1000, "pnl": 50,  "pnl_pct": 5},
        })
        with patch.object(pm, "HISTORY_FILE", hf):
            history = pm.get_portfolio_history()
            dates   = [h["date"] for h in history]
            assert dates == sorted(dates)

    def test_get_portfolio_history_empty_when_no_file(self, tmp_path):
        from components import portfolio as pm
        with patch.object(pm, "HISTORY_FILE", str(tmp_path / "missing.json")):
            assert pm.get_portfolio_history() == []