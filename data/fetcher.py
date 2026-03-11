import requests
import pandas as pd
import os
from datetime import datetime

API_KEY = os.environ.get("ALPHA_VANTAGE_KEY", "")
BASE_URL = "https://www.alphavantage.co/query"

def fetch_stock_data(ticker: str, period: str = "6mo") -> pd.DataFrame:
    try:
        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": ticker,
            "outputsize": "compact",
            "apikey": API_KEY
        }
        r = requests.get(BASE_URL, params=params)
        data = r.json()
        ts = data.get("Time Series (Daily)", {})
        if not ts:
            return pd.DataFrame()
        df = pd.DataFrame.from_dict(ts, orient="index")
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()
        df.columns = ["Open", "High", "Low", "Close", "Volume"]
        df = df.astype(float)

        # Filter by period
        period_days = {"1mo": 30, "3mo": 90, "6mo": 180, "1y": 365, "2y": 730, "5y": 1825}
        days = period_days.get(period, 180)
        df = df[df.index >= pd.Timestamp.now() - pd.Timedelta(days=days)]
        return df
    except Exception as e:
        print(f"Error fetching data for {ticker}: {e}")
        return pd.DataFrame()


def fetch_stock_info(ticker: str) -> dict:
    try:
        params = {
            "function": "OVERVIEW",
            "symbol": ticker,
            "apikey": API_KEY
        }
        r = requests.get(BASE_URL, params=params)
        info = r.json()
        return {
            "name": info.get("Name", ticker),
            "sector": info.get("Sector", "N/A"),
            "market_cap": float(info.get("MarketCapitalization", 0)),
            "pe_ratio": float(info.get("PERatio", 0) or 0),
            "52w_high": float(info.get("52WeekHigh", 0) or 0),
            "52w_low": float(info.get("52WeekLow", 0) or 0),
            "current_price": float(info.get("50DayMovingAverage", 0) or 0),
            "currency": "USD",
        }
    except Exception as e:
        print(f"Error fetching info for {ticker}: {e}")
        return {}


def fetch_news(ticker: str) -> list:
    try:
        params = {
            "function": "NEWS_SENTIMENT",
            "tickers": ticker,
            "limit": 10,
            "apikey": API_KEY
        }
        r = requests.get(BASE_URL, params=params)
        data = r.json()
        results = []
        for item in data.get("feed", [])[:10]:
            results.append({
                "title": item.get("title", "No title"),
                "summary": item.get("summary", ""),
                "url": item.get("url", "#"),
                "publisher": item.get("source", "Unknown"),
                "published": item.get("time_published", ""),
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