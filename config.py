# config.py
import os

# Default stocks to show on load
DEFAULT_TICKER = "AAPL"
DEFAULT_TICKERS = [
    "AAPL",
    "MSFT",
    "TSLA",
    "NVDA",
    "AMZN",
    "GOOGL",
    "META",
    "NFLX",
    "JPM",
    "BRK-B",
    "JNJ",
]

# Chart settings
CHART_THEME = "plotly_dark"
DEFAULT_PERIOD = "6mo"
AVAILABLE_PERIODS = ["1mo", "3mo", "6mo", "1y", "2y", "5y"]

# Technical indicators defaults
RSI_PERIOD = 14
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
BOLLINGER_PERIOD = 20
BOLLINGER_STD = 2

# Portfolio settings
PORTFOLIO_FILE = "portfolio.json"

# App settings
APP_TITLE = "Stock Market Analytics Dashboard"
APP_PORT = int(os.environ.get("PORT", 8050))
DEBUG = os.environ.get("DASH_DEBUG", "false").lower() == "true"