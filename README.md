# 📊 Stock Market Analytics Dashboard

> A real-time stock market analytics dashboard built with Dash and Plotly — search any ticker, view live price data, technical indicators, and portfolio tracking.

[![GitHub](https://img.shields.io/badge/GitHub-Bhanu17291-181717?style=flat&logo=github)](https://github.com/Bhanu17291/stock-analytics)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat&logo=python)](https://python.org)
[![Dash](https://img.shields.io/badge/Dash-Plotly-00B4D8?style=flat&logo=plotly)](https://dash.plotly.com)

---

## 🎯 What It Does

A fully interactive stock market dashboard that lets you:
- Search and analyze **any US or Indian stock** by ticker symbol
- View **real-time OHLCV price data** with candlestick charts
- Track key metrics — **Price, Market Cap, 52W High/Low**
- Compute **technical indicators** automatically
- Manage and track a **personal portfolio**
- Switch between multiple **time periods** (1mo, 3mo, 6mo, 1yr)

---

## 🖥️ Dashboard Preview

```
Stock Market Analytics Dashboard
────────────────────────────────
  Ticker: TSLA          Period: 6mo

  COMPANY          PRICE        MARKET CAP    52W HIGH
  Tesla, Inc.     $391.20       $1.47T        $498.83

  [Candlestick Chart]
  [Volume Chart]
  [Technical Indicators]
  [Portfolio Tracker]
```

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔍 Live Stock Search | Search any ticker (AAPL, TSLA, RELIANCE.NS, etc.) |
| 📈 Candlestick Charts | Interactive OHLCV charts with Plotly |
| 📊 Technical Indicators | RSI, MACD, Bollinger Bands, Moving Averages |
| 💰 Key Metrics | Price, Market Cap, P/E Ratio, 52W High/Low |
| 📁 Portfolio Tracker | Add stocks, track performance, view P&L |
| ⏱️ Time Periods | 1mo, 3mo, 6mo, 1yr, 2yr, 5yr |
| 🌙 Dark Theme | Professional dark UI |

---

## 🚀 Run Locally

```bash
# Clone the repository
git clone https://github.com/Bhanu17291/stock-analytics.git
cd stock-analytics

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\Activate.ps1
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

Open your browser at:
```
http://localhost:8050
```

---

## 📁 Project Structure

```
stock-analytics/
│
├── app.py                  ← Main Dash application entry point
├── config.py               ← App configuration & settings
├── requirements.txt        ← Python dependencies
├── runtime.txt             ← Python version for deployment
├── render.yaml             ← Render.com deployment config
│
├── components/             ← Reusable UI components
├── data/                   ← Data fetching & processing
│   ├── fetcher.py          ← yfinance data fetcher
│   └── indicators.py       ← Technical indicator calculations
├── utils/                  ← Helper utilities
├── assets/                 ← CSS styles & static files
│   └── style.css           ← Custom dark theme styles
├── tests/                  ← Unit tests
│
├── portfolio.json          ← Portfolio data storage
└── portfolio_history.json  ← Portfolio history log
```

---

## 🛠️ Tech Stack

| Tool | Purpose |
|------|---------|
| `Dash` | Web application framework |
| `Plotly` | Interactive charts |
| `Flask` | Backend server |
| `yfinance` | Live stock data |
| `pandas` | Data processing |
| `Python 3.11` | Core language |

---

## 📦 Dependencies

```
dash
plotly
flask
yfinance
pandas
numpy
```

---

## 🌐 Supported Tickers

- **US Stocks:** AAPL, TSLA, MSFT, GOOGL, AMZN, NVDA, META...
- **Indian Stocks:** RELIANCE.NS, TCS.NS, INFY.NS, HDFCBANK.NS...
- **Indices:** ^GSPC (S&P500), ^NSEI (Nifty50), ^IXIC (Nasdaq)
- **Crypto:** BTC-USD, ETH-USD

---

## ⚠️ Disclaimer

This dashboard is for **educational and informational purposes only**. It is not financial advice. Always conduct independent research before making investment decisions.

---

*Built with ❤️ using Dash & Plotly*