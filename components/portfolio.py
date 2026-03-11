# components/portfolio.py
import json
import logging
import os
import shutil
from datetime import datetime, date
from typing import Any

from config import PORTFOLIO_FILE
from data.fetcher import fetch_many, get_current_price

logger = logging.getLogger(__name__)

HISTORY_FILE = "portfolio_history.json"


# ── JSON helpers ──────────────────────────────────────────────────────────────

def _safe_load(path: str, default: Any) -> Any:
    """
    Load JSON from path. On any failure (missing, corrupt, permission),
    attempt to restore from a .bak backup, then return default.
    """
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        logger.warning("Corrupt or unreadable file: %s — trying backup", path)
        bak = path + ".bak"
        if os.path.exists(bak):
            try:
                with open(bak, "r", encoding="utf-8") as f:
                    data = json.load(f)
                logger.info("Restored %s from backup", path)
                return data
            except (json.JSONDecodeError, OSError):
                logger.error("Backup also corrupt: %s", bak)
        return default


def _safe_save(path: str, data: Any) -> None:
    """
    Save data as JSON. Creates a .bak of the previous version first
    so we can recover if a write is interrupted.
    """
    if os.path.exists(path):
        try:
            shutil.copy2(path, path + ".bak")
        except OSError:
            logger.warning("Could not create backup for %s", path)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except OSError:
        logger.exception("Failed to save %s", path)
        raise


# ── Validation ────────────────────────────────────────────────────────────────

def _validate(ticker: str, shares: float, buy_price: float) -> None:
    """Raise ValueError with a clear message if inputs are invalid."""
    ticker = ticker.strip()
    if not ticker:
        raise ValueError("Ticker symbol cannot be empty.")
    if not ticker.replace(".", "").replace("-", "").isalnum():
        raise ValueError(f"Invalid ticker symbol: '{ticker}'.")
    if shares <= 0:
        raise ValueError("Shares must be greater than zero.")
    if buy_price <= 0:
        raise ValueError("Buy price must be greater than zero.")


# ── Core Portfolio I/O ────────────────────────────────────────────────────────

def load_portfolio() -> dict:
    """Load portfolio from JSON file, returning {} on any failure."""
    return _safe_load(PORTFOLIO_FILE, {})


def save_portfolio(portfolio: dict) -> None:
    """Save portfolio to JSON file with backup protection."""
    _safe_save(PORTFOLIO_FILE, portfolio)


def add_stock(ticker: str, shares: float, buy_price: float) -> dict:
    """
    Add or update a stock in the portfolio.
    Raises ValueError if inputs are invalid.
    """
    ticker = ticker.upper().strip()
    _validate(ticker, shares, buy_price)

    portfolio = load_portfolio()
    portfolio[ticker] = {
        "shares":    round(float(shares),    6),
        "buy_price": round(float(buy_price), 6),
        "added_at":  datetime.now().isoformat(),
    }
    save_portfolio(portfolio)
    logger.info("Added %s to portfolio (shares=%.4f, buy=%.4f)", ticker, shares, buy_price)
    return portfolio


def remove_stock(ticker: str) -> dict:
    """Remove a stock from the portfolio. Silent no-op if not found."""
    ticker = ticker.upper().strip()
    portfolio = load_portfolio()
    if ticker in portfolio:
        del portfolio[ticker]
        save_portfolio(portfolio)
        logger.info("Removed %s from portfolio", ticker)
    else:
        logger.warning("Tried to remove %s but it wasn't in portfolio", ticker)
    return portfolio


# ── Summary & Totals ──────────────────────────────────────────────────────────

def get_portfolio_summary() -> list:
    """
    Return per-stock summary with current prices and P&L.
    Fetches all prices in parallel using fetch_many.
    """
    portfolio = load_portfolio()
    if not portfolio:
        return []

    tickers = list(portfolio.keys())

    # Parallel price fetch — one network round-trip for all tickers
    try:
        price_data = fetch_many(tickers, period="5d")
        prices = {}
        for ticker, df in price_data.items():
            if not df.empty:
                prices[ticker] = round(float(df["Close"].iloc[-1]), 2)
            else:
                prices[ticker] = get_current_price(ticker)   # individual fallback
    except Exception:
        logger.exception("Parallel fetch failed, falling back to individual fetches")
        prices = {t: get_current_price(t) for t in tickers}

    summary = []
    for ticker, data in portfolio.items():
        shares      = float(data["shares"])
        buy_price   = float(data["buy_price"])
        curr_price  = prices.get(ticker, 0.0)

        invested      = round(shares * buy_price,  2)
        current_value = round(shares * curr_price, 2)
        pnl           = round(current_value - invested, 2)
        pnl_pct       = round((pnl / invested) * 100, 2) if invested > 0 else 0.0

        summary.append({
            "ticker":        ticker,
            "shares":        shares,
            "buy_price":     buy_price,
            "current_price": curr_price,
            "invested":      invested,
            "current_value": current_value,
            "pnl":           pnl,
            "pnl_pct":       pnl_pct,
            "color":         "success" if pnl >= 0 else "danger",
        })

    return summary


def get_portfolio_totals() -> dict:
    """Return total invested, current value, and overall P&L."""
    summary = get_portfolio_summary()
    if not summary:
        return {"invested": 0.0, "current_value": 0.0, "pnl": 0.0, "pnl_pct": 0.0}

    total_invested = sum(s["invested"]      for s in summary)
    total_value    = sum(s["current_value"] for s in summary)
    total_pnl      = round(total_value - total_invested, 2)
    total_pnl_pct  = round((total_pnl / total_invested) * 100, 2) if total_invested > 0 else 0.0

    return {
        "invested":      round(total_invested, 2),
        "current_value": round(total_value,    2),
        "pnl":           total_pnl,
        "pnl_pct":       total_pnl_pct,
    }


# ── History Snapshots ─────────────────────────────────────────────────────────

def record_portfolio_snapshot() -> None:
    """
    Save today's total portfolio value as a snapshot.
    Called once per day — if today's snapshot already exists, it's updated.
    """
    totals  = get_portfolio_totals()
    history = _safe_load(HISTORY_FILE, {})

    today = date.today().isoformat()
    history[today] = {
        "invested":      totals["invested"],
        "current_value": totals["current_value"],
        "pnl":           totals["pnl"],
        "pnl_pct":       totals["pnl_pct"],
    }

    _safe_save(HISTORY_FILE, history)
    logger.info("Portfolio snapshot saved for %s: value=%.2f", today, totals["current_value"])


def get_portfolio_history() -> list:
    """
    Return portfolio value history as a sorted list of dicts.
    Each entry: { date, invested, current_value, pnl, pnl_pct }
    """
    history = _safe_load(HISTORY_FILE, {})
    return sorted(
        [{"date": k, **v} for k, v in history.items()],
        key=lambda x: x["date"],
    )