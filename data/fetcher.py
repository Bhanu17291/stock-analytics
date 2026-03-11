# data/fetcher.py
import yfinance as yf
import pandas as pd


def fetch_stock_data(ticker: str, period: str = "6mo") -> pd.DataFrame:
    """Fetch OHLCV stock data from Yahoo Finance."""
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period)
        if df.empty:
            return pd.DataFrame()
        df.index = pd.to_datetime(df.index)
        df.index = df.index.tz_localize(None)
        return df
    except Exception as e:
        print(f"Error fetching data for {ticker}: {e}")
        return pd.DataFrame()


def fetch_stock_info(ticker: str) -> dict:
    """Fetch company info and current price."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        return {
            "name": info.get("longName", ticker),
            "sector": info.get("sector", "N/A"),
            "market_cap": info.get("marketCap", 0),
            "pe_ratio": info.get("trailingPE", 0),
            "52w_high": info.get("fiftyTwoWeekHigh", 0),
            "52w_low": info.get("fiftyTwoWeekLow", 0),
            "current_price": info.get("currentPrice", info.get("regularMarketPrice", 0)),
            "currency": info.get("currency", "USD"),
        }
    except Exception as e:
        print(f"Error fetching info for {ticker}: {e}")
        return {}


def fetch_news(ticker: str) -> list:
    """Fetch latest news for a ticker."""
    try:
        stock = yf.Ticker(ticker)
        news = stock.news
        results = []
        for item in news[:10]:
            content = item.get("content", {})
            results.append({
                "title": content.get("title", "No title"),
                "summary": content.get("summary", ""),
                "url": content.get("canonicalUrl", {}).get("url", "#"),
                "publisher": content.get("provider", {}).get("displayName", "Unknown"),
                "published": content.get("pubDate", ""),
            })
        return results
    except Exception as e:
        print(f"Error fetching news for {ticker}: {e}")
        return []


def get_current_price(ticker: str) -> float:
    """Get the latest closing price."""
    try:
        df = fetch_stock_data(ticker, period="5d")
        if not df.empty:
            close = df["Close"]
            if hasattr(close, 'columns'):
                close = close.iloc[:, 0]
            return round(float(close.iloc[-1]), 2)
        return 0.0
    except:
        return 0.0