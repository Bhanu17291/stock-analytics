# components/portfolio.py
import json
import os
from data.fetcher import get_current_price
from config import PORTFOLIO_FILE


def load_portfolio() -> dict:
    """Load portfolio from JSON file."""
    if os.path.exists(PORTFOLIO_FILE):
        with open(PORTFOLIO_FILE, "r") as f:
            return json.load(f)
    return {}


def save_portfolio(portfolio: dict):
    """Save portfolio to JSON file."""
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(portfolio, f, indent=2)


def add_stock(ticker: str, shares: float, buy_price: float):
    """Add or update a stock in the portfolio."""
    portfolio = load_portfolio()
    ticker = ticker.upper().strip()
    portfolio[ticker] = {
        "shares": shares,
        "buy_price": buy_price,
    }
    save_portfolio(portfolio)
    return portfolio


def remove_stock(ticker: str):
    """Remove a stock from the portfolio."""
    portfolio = load_portfolio()
    ticker = ticker.upper().strip()
    if ticker in portfolio:
        del portfolio[ticker]
        save_portfolio(portfolio)
    return portfolio


def get_portfolio_summary() -> list:
    """Get full portfolio with current prices and P&L."""
    portfolio = load_portfolio()
    summary = []

    for ticker, data in portfolio.items():
        shares = data["shares"]
        buy_price = data["buy_price"]
        current_price = get_current_price(ticker)

        invested = round(shares * buy_price, 2)
        current_value = round(shares * current_price, 2)
        pnl = round(current_value - invested, 2)
        pnl_pct = round((pnl / invested) * 100, 2) if invested > 0 else 0

        summary.append({
            "ticker": ticker,
            "shares": shares,
            "buy_price": buy_price,
            "current_price": current_price,
            "invested": invested,
            "current_value": current_value,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
            "color": "success" if pnl >= 0 else "danger",
        })

    return summary


def get_portfolio_totals() -> dict:
    """Get total invested, current value and overall P&L."""
    summary = get_portfolio_summary()
    if not summary:
        return {"invested": 0, "current_value": 0, "pnl": 0, "pnl_pct": 0}

    total_invested = sum(s["invested"] for s in summary)
    total_value = sum(s["current_value"] for s in summary)
    total_pnl = round(total_value - total_invested, 2)
    total_pnl_pct = round((total_pnl / total_invested) * 100, 2) if total_invested > 0 else 0

    return {
        "invested": round(total_invested, 2),
        "current_value": round(total_value, 2),
        "pnl": total_pnl,
        "pnl_pct": total_pnl_pct,
    }