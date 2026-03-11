import requests
import pandas as pd
import os


def fetch_stock_data(ticker: str, period: str = "6mo") -> pd.DataFrame:
    try:
        period_map = {"1mo": "1mo", "3mo": "3mo", "6mo": "6mo", "1y": "1y", "2y": "2y", "5y": "5y"}
        yf_period = period_map.get(period, "6mo")
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
        params = {"range": yf_period, "interval": "1d"}
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
        }
        r = requests.get(url, params=params, headers=headers, timeout=10)
        data = r.json()
        result = data["chart"]["result"][0]
        timestamps = result["timestamp"]
        ohlcv = result["indicators"]["quote"][0]
        df = pd.DataFrame({
            "Open": ohlcv["open"],
            "High": ohlcv["high"],
            "Low": ohlcv["low"],
            "Close": ohlcv["close"],
            "Volume": ohlcv["volume"],
        }, index=pd.to_datetime(timestamps, unit="s"))
        df.index = df.index.tz_localize(None)
        df = df.dropna()
        return df
    except Exception as e:
        print(f"Error fetching data for {ticker}: {e}")
        return pd.DataFrame()


def fetch_stock_info(ticker: str) -> dict:
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
        params = {"range": "1d", "interval": "1d"}
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        r = requests.get(url, params=params, headers=headers, timeout=10)
        data = r.json()
        result = data["chart"]["result"][0]
        meta = result["meta"]
        return {
            "name": meta.get("longName", meta.get("shortName", ticker)),
            "sector": "N/A",
            "market_cap": 0,
            "pe_ratio": 0,
            "52w_high": meta.get("fiftyTwoWeekHigh", 0),
            "52w_low": meta.get("fiftyTwoWeekLow", 0),
            "current_price": meta.get("regularMarketPrice", 0),
            "currency": meta.get("currency", "USD"),
        }
    except Exception as e:
        print(f"Error fetching info for {ticker}: {e}")
        return {}


def fetch_news(ticker: str) -> list:
    try:
        url = "https://query1.finance.yahoo.com/v1/finance/search"
        params = {"q": ticker, "newsCount": 10}
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        r = requests.get(url, params=params, headers=headers, timeout=10)
        data = r.json()
        results = []
        for item in data.get("news", [])[:10]:
            results.append({
                "title": item.get("title", "No title"),
                "summary": "",
                "url": item.get("link", "#"),
                "publisher": item.get("publisher", "Unknown"),
                "published": item.get("providerPublishTime", ""),
            })
        return results
    except Exception as e:
        print(f"Error fetching news for {ticker}: {e}")
        return []


def get_current_price(ticker: str) -> float:
    try:
        df = fetch_stock_data(ticker, period="5d")
        if not df.empty:
            return round(float(df["Close"].iloc[-1]), 2)
        return 0.0
    except:
        return 0.0