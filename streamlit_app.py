"""
Stock Analytics — Streamlit version
Converted from Dash/dbc to Streamlit.
Run:  streamlit run streamlit_app.py
"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime, date
import json, os, shutil, logging

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="📈 Stock Analytics",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Dark theme CSS ────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Overall background */
    .stApp { background-color: #0d0d1a; color: #e0e0e0; }
    [data-testid="stSidebar"] { background-color: #12122a; }

    /* Metric cards */
    [data-testid="stMetricValue"] { color: #ffffff; font-size: 1.1rem; font-weight: 700; }
    [data-testid="stMetricLabel"] { color: #9b9bb4; font-size: 0.75rem; }
    [data-testid="metric-container"] {
        background: #1e1e2e;
        border: 1px solid #2e2e4e;
        border-radius: 10px;
        padding: 12px 16px;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { background-color: #12122a; border-radius: 8px; }
    .stTabs [data-baseweb="tab"] { color: #9b9bb4; }
    .stTabs [aria-selected="true"] { color: #6366f1 !important; border-bottom-color: #6366f1 !important; }

    /* Inputs */
    .stTextInput > div > div > input,
    .stSelectbox > div > div { background-color: #1a1a2e !important; color: #e0e0e0 !important; border-color: #2e2e4e !important; }
    .stNumberInput input { background-color: #1a1a2e !important; color: #e0e0e0 !important; }

    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #6366f1, #8b5cf6);
        color: white; border: none; border-radius: 8px;
        font-weight: 600; transition: opacity 0.2s;
    }
    .stButton > button:hover { opacity: 0.85; }

    /* Tables */
    .stDataFrame { background-color: #1e1e2e; }
    thead tr th { background-color: #2e2e4e !important; color: #e0e0e0 !important; }

    /* Live dot */
    .live-dot {
        display: inline-block; width: 8px; height: 8px;
        background: #26a69a; border-radius: 50%;
        animation: pulse 1.5s infinite; margin-right: 8px;
    }
    @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }

    /* Navbar */
    .navbar-band {
        background: linear-gradient(90deg, #12122a 0%, #1a1a3e 100%);
        border-bottom: 1px solid #2e2e4e;
        padding: 10px 24px; border-radius: 10px;
        margin-bottom: 1.2rem;
        display: flex; align-items: center; justify-content: space-between;
    }
    .navbar-title { font-size: 1.2rem; font-weight: 700; color: #e0e0e0; letter-spacing: 0.5px; }
    .badge-updated { font-size: 0.7rem; color: #6b6b9a; }
    .price-up   { color: #26a69a; font-weight: 700; }
    .price-down { color: #ef5350; font-weight: 700; }

    hr { border-color: #2e2e4e; }
    h1,h2,h3,h4,h5 { color: #e0e0e0; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# DATA LAYER  (inline — mirrors data/fetcher.py & data/indicators.py)
# ══════════════════════════════════════════════════════════════════════════════

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PORTFOLIO_FILE = "portfolio.json"
HISTORY_FILE   = "portfolio_history.json"

# ── yfinance helpers ──────────────────────────────────────────────────────────

@st.cache_data(ttl=900, show_spinner=False)   # 15 min cache
def fetch_stock_data(ticker: str, period: str = "6mo") -> pd.DataFrame:
    try:
        import yfinance as yf
        df = yf.download(ticker, period=period, interval="1d", progress=False, auto_adjust=True)
        if df.empty:
            return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.index = pd.to_datetime(df.index).tz_localize(None)
        return df.dropna()
    except Exception as e:
        logger.error("fetch_stock_data error: %s", e)
        return pd.DataFrame()


@st.cache_data(ttl=3600, show_spinner=False)  # 1 hour cache
def fetch_stock_info(ticker: str) -> dict:
    try:
        import yfinance as yf
        t    = yf.Ticker(ticker)
        meta = t.info or {}

        price = meta.get("currentPrice") or meta.get("regularMarketPrice") or 0.0
        high  = meta.get("fiftyTwoWeekHigh") or 0.0
        low   = meta.get("fiftyTwoWeekLow")  or 0.0

        if not price:
            df = fetch_stock_data(ticker, "1y")
            if not df.empty:
                price = round(float(df["Close"].iloc[-1]), 2)
                high  = round(float(df["High"].max()), 2)
                low   = round(float(df["Low"].min()),  2)

        if not price:
            return {}

        currency = meta.get("currency") or ("INR" if ticker.endswith((".BO", ".NS")) else "USD")

        return {
            "ticker":        ticker,
            "name":          meta.get("longName") or meta.get("shortName") or ticker,
            "sector":        meta.get("sector") or "N/A",
            "market_cap":    meta.get("marketCap") or 0.0,
            "pe_ratio":      meta.get("trailingPE") or 0.0,
            "current_price": price,
            "52w_high":      high,
            "52w_low":       low,
            "currency":      currency,
        }
    except Exception as e:
        logger.error("fetch_stock_info error: %s", e)
        return {}


@st.cache_data(ttl=1800, show_spinner=False)  # 30 min cache
def fetch_news(ticker: str) -> list:
    try:
        import yfinance as yf
        t   = yf.Ticker(ticker)
        raw = t.news or []
        results = []
        for item in raw[:10]:
            content = item.get("content", {})
            results.append({
                "title":     content.get("title") or item.get("title") or "No title",
                "summary":   content.get("summary") or "",
                "url":       (content.get("canonicalUrl", {}) or {}).get("url") or item.get("link") or "#",
                "publisher": (content.get("provider", {}) or {}).get("displayName") or item.get("publisher") or "Unknown",
                "published": str(content.get("pubDate", "")),
            })
        return results
    except Exception as e:
        logger.error("fetch_news error: %s", e)
        return []


def get_current_price(ticker: str) -> float:
    df = fetch_stock_data(ticker, "5d")
    if not df.empty:
        return round(float(df["Close"].iloc[-1]), 2)
    info = fetch_stock_info(ticker)
    return round(float(info.get("current_price", 0.0)), 2)

# ── Technical Indicators ──────────────────────────────────────────────────────

def get_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    close = df["Close"].squeeze()

    # EMA 20 / SMA 50
    df["EMA_20"] = close.ewm(span=20, adjust=False).mean()
    df["SMA_50"] = close.rolling(window=50).mean()

    # Bollinger Bands (20, 2)
    bb_mid = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    df["BB_Upper"]  = bb_mid + 2 * bb_std
    df["BB_Middle"] = bb_mid
    df["BB_Lower"]  = bb_mid - 2 * bb_std

    # RSI 14
    delta = close.diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    rs    = gain / loss.replace(0, float("nan"))
    df["RSI"] = 100 - 100 / (1 + rs)

    # MACD (12, 26, 9)
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    df["MACD"]        = ema12 - ema26
    df["MACD_Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_Hist"]   = df["MACD"] - df["MACD_Signal"]

    return df

# ── Formatting helpers ────────────────────────────────────────────────────────

def fmt_market_cap(val: float) -> str:
    if val >= 1e12: return f"${val/1e12:.2f}T"
    if val >= 1e9:  return f"${val/1e9:.2f}B"
    if val >= 1e6:  return f"${val/1e6:.2f}M"
    return f"${val:,.0f}"

def currency_symbol(currency: str) -> str:
    return {"USD": "$", "INR": "₹", "EUR": "€", "GBP": "£", "JPY": "¥"}.get(currency, "$")

# ══════════════════════════════════════════════════════════════════════════════
# PORTFOLIO LAYER  (mirrors components/portfolio.py)
# ══════════════════════════════════════════════════════════════════════════════

def _safe_load(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        bak = path + ".bak"
        if os.path.exists(bak):
            try:
                with open(bak, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return default

def _safe_save(path, data):
    if os.path.exists(path):
        try: shutil.copy2(path, path + ".bak")
        except OSError: pass
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def load_portfolio() -> dict:
    return _safe_load(PORTFOLIO_FILE, {})

def save_portfolio(portfolio: dict):
    _safe_save(PORTFOLIO_FILE, portfolio)

def add_stock(ticker: str, shares: float, buy_price: float):
    ticker = ticker.upper().strip()
    if shares <= 0 or buy_price <= 0:
        raise ValueError("Shares and buy price must be > 0.")
    portfolio = load_portfolio()
    portfolio[ticker] = {
        "shares":    round(float(shares), 6),
        "buy_price": round(float(buy_price), 6),
        "added_at":  datetime.now().isoformat(),
    }
    save_portfolio(portfolio)

def remove_stock(ticker: str):
    ticker = ticker.upper().strip()
    portfolio = load_portfolio()
    if ticker in portfolio:
        del portfolio[ticker]
        save_portfolio(portfolio)

def get_portfolio_summary() -> list:
    portfolio = load_portfolio()
    if not portfolio:
        return []
    summary = []
    for ticker, data in portfolio.items():
        shares    = float(data["shares"])
        buy_price = float(data["buy_price"])
        curr      = get_current_price(ticker)
        invested  = round(shares * buy_price, 2)
        value     = round(shares * curr, 2)
        pnl       = round(value - invested, 2)
        pnl_pct   = round((pnl / invested) * 100, 2) if invested else 0.0
        summary.append({
            "ticker": ticker, "shares": shares, "buy_price": buy_price,
            "current_price": curr, "invested": invested,
            "current_value": value, "pnl": pnl, "pnl_pct": pnl_pct,
        })
    return summary

def get_portfolio_totals() -> dict:
    s = get_portfolio_summary()
    if not s:
        return {"invested": 0.0, "current_value": 0.0, "pnl": 0.0, "pnl_pct": 0.0}
    inv = sum(x["invested"] for x in s)
    val = sum(x["current_value"] for x in s)
    pnl = round(val - inv, 2)
    return {"invested": round(inv,2), "current_value": round(val,2),
            "pnl": pnl, "pnl_pct": round((pnl/inv)*100,2) if inv else 0.0}

def record_portfolio_snapshot():
    totals  = get_portfolio_totals()
    history = _safe_load(HISTORY_FILE, {})
    today   = date.today().isoformat()
    history[today] = totals
    _safe_save(HISTORY_FILE, history)

def get_portfolio_history() -> list:
    history = _safe_load(HISTORY_FILE, {})
    return sorted([{"date": k, **v} for k, v in history.items()], key=lambda x: x["date"])

# ══════════════════════════════════════════════════════════════════════════════
# CHART BUILDERS  (mirrors components/charts.py & portfolio_charts.py)
# ══════════════════════════════════════════════════════════════════════════════

CHART_BG = "#1e1e2e"

def build_candlestick_chart(ticker: str, period: str) -> go.Figure:
    df = fetch_stock_data(ticker, period)
    if df.empty:
        return go.Figure()
    df = get_all_indicators(df)

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        vertical_spacing=0.03, row_heights=[0.75, 0.25])

    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"],
        low=df["Low"], close=df["Close"], name=ticker,
        increasing_line_color="#26a69a", decreasing_line_color="#ef5350"
    ), row=1, col=1)

    for col, name, color, dash, fill in [
        ("BB_Upper",  "BB Upper",  "rgba(173,216,230,0.6)", "solid",  False),
        ("BB_Middle", "BB Middle", "rgba(255,255,255,0.4)", "dash",   False),
        ("BB_Lower",  "BB Lower",  "rgba(173,216,230,0.6)", "solid",  True),
    ]:
        kwargs = dict(x=df.index, y=df[col], name=name,
                      line=dict(color=color, width=1, dash=dash))
        if fill:
            kwargs.update(fill="tonexty", fillcolor="rgba(173,216,230,0.05)")
        fig.add_trace(go.Scatter(**kwargs), row=1, col=1)

    fig.add_trace(go.Scatter(x=df.index, y=df["EMA_20"], name="EMA 20",
                             line=dict(color="#ff9800", width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["SMA_50"], name="SMA 50",
                             line=dict(color="#ab47bc", width=1.5)), row=1, col=1)

    colors = ["#26a69a" if c >= o else "#ef5350"
              for c, o in zip(df["Close"].squeeze(), df["Open"].squeeze())]
    fig.add_trace(go.Bar(x=df.index, y=df["Volume"].squeeze(),
                         name="Volume", marker_color=colors, opacity=0.7), row=2, col=1)

    fig.update_layout(
        template="plotly_dark", title=f"{ticker} — Price Chart",
        xaxis_rangeslider_visible=False, height=580,
        margin=dict(l=40, r=40, t=50, b=40),
        paper_bgcolor=CHART_BG, plot_bgcolor=CHART_BG,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def build_rsi_chart(ticker: str, period: str) -> go.Figure:
    df = fetch_stock_data(ticker, period)
    if df.empty:
        return go.Figure()
    df = get_all_indicators(df)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df["RSI"], name="RSI",
                             line=dict(color="#42a5f5", width=2)))
    fig.add_hline(y=70, line_dash="dash", line_color="#ef5350",
                  annotation_text="Overbought (70)")
    fig.add_hline(y=30, line_dash="dash", line_color="#26a69a",
                  annotation_text="Oversold (30)")
    fig.add_hrect(y0=30, y1=70, fillcolor="rgba(255,255,255,0.03)", line_width=0)
    fig.update_layout(template="plotly_dark", title=f"{ticker} — RSI (14)",
                      height=300, yaxis=dict(range=[0, 100]),
                      paper_bgcolor=CHART_BG, plot_bgcolor=CHART_BG,
                      margin=dict(l=40, r=40, t=50, b=40))
    return fig


def build_macd_chart(ticker: str, period: str) -> go.Figure:
    df = fetch_stock_data(ticker, period)
    if df.empty:
        return go.Figure()
    df = get_all_indicators(df)
    hist = df["MACD_Hist"].squeeze()
    colors = ["#26a69a" if v >= 0 else "#ef5350" for v in hist]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df.index, y=hist, name="Histogram",
                         marker_color=colors, opacity=0.7))
    fig.add_trace(go.Scatter(x=df.index, y=df["MACD"].squeeze(),
                             name="MACD", line=dict(color="#42a5f5", width=2)))
    fig.add_trace(go.Scatter(x=df.index, y=df["MACD_Signal"].squeeze(),
                             name="Signal", line=dict(color="#ff9800", width=2)))
    fig.update_layout(template="plotly_dark", title=f"{ticker} — MACD",
                      height=300, paper_bgcolor=CHART_BG, plot_bgcolor=CHART_BG,
                      margin=dict(l=40, r=40, t=50, b=40))
    return fig


def build_allocation_chart() -> go.Figure:
    summary = get_portfolio_summary()
    if not summary:
        return go.Figure()
    labels = [s["ticker"] for s in summary]
    values = [s["current_value"] for s in summary]
    fig = go.Figure(go.Pie(labels=labels, values=values, hole=0.45,
                           marker=dict(colors=["#6366f1","#26a69a","#ff9800",
                                               "#42a5f5","#ab47bc","#ef5350"]),
                           textinfo="label+percent"))
    fig.update_layout(template="plotly_dark", title="Portfolio Allocation",
                      height=350, paper_bgcolor=CHART_BG, plot_bgcolor=CHART_BG,
                      margin=dict(l=20, r=20, t=50, b=20))
    return fig


def build_pnl_history_chart() -> go.Figure:
    history = get_portfolio_history()
    if len(history) < 2:
        return go.Figure()
    dates  = [h["date"] for h in history]
    values = [h["current_value"] for h in history]
    fig = go.Figure(go.Scatter(x=dates, y=values, fill="tozeroy",
                               line=dict(color="#6366f1", width=2),
                               fillcolor="rgba(99,102,241,0.15)", name="Portfolio Value"))
    fig.update_layout(template="plotly_dark", title="Portfolio Value History",
                      height=350, paper_bgcolor=CHART_BG, plot_bgcolor=CHART_BG,
                      margin=dict(l=40, r=40, t=50, b=40))
    return fig

# ══════════════════════════════════════════════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════════════════════════════════════════════

STOCK_OPTIONS = {
    "AAPL":  "🇺🇸 Apple Inc. (AAPL)",
    "MSFT":  "🇺🇸 Microsoft (MSFT)",
    "TSLA":  "🇺🇸 Tesla (TSLA)",
    "NVDA":  "🇺🇸 NVIDIA (NVDA)",
    "AMZN":  "🇺🇸 Amazon (AMZN)",
    "GOOGL": "🇺🇸 Alphabet / Google (GOOGL)",
    "META":  "🇺🇸 Meta (META)",
    "NFLX":  "🇺🇸 Netflix (NFLX)",
    "JPM":   "🇺🇸 JPMorgan Chase (JPM)",
    "BRK-B": "🇺🇸 Berkshire Hathaway (BRK-B)",
    "JNJ":   "🇺🇸 Johnson & Johnson (JNJ)",
}
AVAILABLE_PERIODS = ["1mo", "3mo", "6mo", "1y", "2y", "5y"]

if "ticker"  not in st.session_state: st.session_state.ticker  = "AAPL"
if "period"  not in st.session_state: st.session_state.period  = "6mo"
if "p_msg"   not in st.session_state: st.session_state.p_msg   = ""
if "p_msg_t" not in st.session_state: st.session_state.p_msg_t = "info"

# ══════════════════════════════════════════════════════════════════════════════
# NAVBAR
# ══════════════════════════════════════════════════════════════════════════════

now = datetime.now().strftime("%H:%M:%S")
st.markdown(f"""
<div class="navbar-band">
  <div style="display:flex;align-items:center">
    <span class="live-dot"></span>
    <span class="navbar-title">📈 Stock Analytics</span>
  </div>
  <div>
    <span style="color:#9b9bb4;font-size:0.8rem">Real-time Market Analytics</span>
    &nbsp;&nbsp;
    <span class="badge-updated">↻ Updated {now}</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR — SEARCH CONTROLS
# ══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("### 🔍 Stock Search")
    quick = st.selectbox("⚡ Quick select", [""] + list(STOCK_OPTIONS.keys()),
                         format_func=lambda x: STOCK_OPTIONS.get(x, "— select a stock —") if x else "— select a stock —")
    if quick:
        st.session_state.ticker = quick

    ticker_input = st.text_input("Or type any ticker", value=st.session_state.ticker,
                                 placeholder="e.g. AAPL, TSLA, RELIANCE.NS")
    period_sel   = st.selectbox("Period", AVAILABLE_PERIODS,
                                index=AVAILABLE_PERIODS.index(st.session_state.period))

    col_a, col_b = st.columns([3, 1])
    with col_a:
        analyze = st.button("🔍 Analyze", use_container_width=True)
    with col_b:
        refresh = st.button("🔄", use_container_width=True, help="Refresh data")

    if analyze:
        t = ticker_input.strip().upper()
        if t:
            st.session_state.ticker = t
            st.session_state.period = period_sel
            fetch_stock_data.clear()
            fetch_stock_info.clear()
            fetch_news.clear()
        else:
            st.error("Please enter a valid ticker symbol.")

    if refresh:
        fetch_stock_data.clear()
        fetch_stock_info.clear()
        fetch_news.clear()
        st.rerun()

    st.divider()
    st.markdown("### 💼 Add to Portfolio")
    p_ticker = st.text_input("Ticker",    placeholder="e.g. AAPL")
    p_shares = st.number_input("Shares",  min_value=0.0, step=0.1, format="%.4f")
    p_price  = st.number_input("Buy Price ($)", min_value=0.0, step=0.01, format="%.2f")

    col_add, col_rem = st.columns(2)
    with col_add:
        if st.button("➕ Add", use_container_width=True):
            if p_ticker and p_shares > 0 and p_price > 0:
                try:
                    add_stock(p_ticker, p_shares, p_price)
                    st.session_state.p_msg   = f"✅ {p_ticker.upper()} added!"
                    st.session_state.p_msg_t = "success"
                except Exception as e:
                    st.session_state.p_msg   = f"❌ {e}"
                    st.session_state.p_msg_t = "error"
            else:
                st.session_state.p_msg   = "⚠️ Fill in all fields."
                st.session_state.p_msg_t = "warning"
    with col_rem:
        if st.button("🗑️ Remove", use_container_width=True):
            if p_ticker:
                try:
                    remove_stock(p_ticker)
                    st.session_state.p_msg   = f"🗑️ {p_ticker.upper()} removed."
                    st.session_state.p_msg_t = "info"
                except Exception as e:
                    st.session_state.p_msg   = f"❌ {e}"
                    st.session_state.p_msg_t = "error"
            else:
                st.session_state.p_msg   = "⚠️ Enter a ticker to remove."
                st.session_state.p_msg_t = "warning"

    if st.session_state.p_msg:
        t = st.session_state.p_msg_t
        fn = {"success": st.success, "error": st.error,
              "warning": st.warning, "info": st.info}.get(t, st.info)
        fn(st.session_state.p_msg)

# ══════════════════════════════════════════════════════════════════════════════
# INFO CARDS
# ══════════════════════════════════════════════════════════════════════════════

ticker = st.session_state.ticker
period = st.session_state.period

with st.spinner(f"Loading {ticker}…"):
    info = fetch_stock_info(ticker)

if not info:
    st.error(f"⚠️ Could not load data for **{ticker}**. Check the ticker symbol and try again.")
    st.stop()

sym   = currency_symbol(info.get("currency", "USD"))
price = info.get("current_price", 0)

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("🏢 Company",    info.get("name", ticker))
c2.metric("💰 Price",      f"{sym}{price:,.2f}")
c3.metric("📊 Market Cap", fmt_market_cap(info.get("market_cap", 0)))
c4.metric("📈 52W High",   f"{sym}{info.get('52w_high', 0):,.2f}")
c5.metric("📉 52W Low",    f"{sym}{info.get('52w_low',  0):,.2f}")
c6.metric("🏭 Sector",     info.get("sector", "N/A"))

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════

tab_chart, tab_ind, tab_port, tab_news = st.tabs([
    "📈 Price Chart", "📊 Indicators", "💼 Portfolio", "📰 News & Sentiment"
])

# ── TAB 1 : Price Chart ───────────────────────────────────────────────────────
with tab_chart:
    with st.spinner("Building candlestick chart…"):
        fig = build_candlestick_chart(ticker, period)
    if not fig.data:
        st.warning(f"No price data available for **{ticker}**.")
    else:
        st.plotly_chart(fig, use_container_width=True)

# ── TAB 2 : Indicators ───────────────────────────────────────────────────────
with tab_ind:
    with st.spinner("Computing indicators…"):
        rsi_fig  = build_rsi_chart(ticker, period)
        macd_fig = build_macd_chart(ticker, period)

    if not rsi_fig.data and not macd_fig.data:
        st.warning(f"No indicator data for **{ticker}**.")
    else:
        if rsi_fig.data:
            st.plotly_chart(rsi_fig,  use_container_width=True)
        if macd_fig.data:
            st.plotly_chart(macd_fig, use_container_width=True)

# ── TAB 3 : Portfolio ────────────────────────────────────────────────────────
with tab_port:
    record_portfolio_snapshot()
    summary = get_portfolio_summary()
    totals  = get_portfolio_totals()

    # Portfolio chart row
    col_alloc, col_hist = st.columns([5, 7])
    with col_alloc:
        af = build_allocation_chart()
        if af.data:
            st.plotly_chart(af, use_container_width=True)
        else:
            st.info("📊 Add stocks to see allocation.")
    with col_hist:
        hf = build_pnl_history_chart()
        if hf.data:
            st.plotly_chart(hf, use_container_width=True)
        else:
            st.info("📈 Come back tomorrow to see value history.")

    # Portfolio table
    if not summary:
        st.info("💼 Your portfolio is empty. Add stocks from the sidebar.")
    else:
        # Build DataFrame for display
        rows = []
        for s in summary:
            pnl_str = f"{'+'if s['pnl']>=0 else ''}{s['pnl']:,.2f} ({'+' if s['pnl_pct']>=0 else ''}{s['pnl_pct']}%)"
            rows.append({
                "Ticker":        s["ticker"],
                "Shares":        s["shares"],
                "Buy Price":     f"${s['buy_price']:,.2f}",
                "Current Price": f"${s['current_price']:,.2f}",
                "Invested":      f"${s['invested']:,.2f}",
                "Value":         f"${s['current_value']:,.2f}",
                "P&L":           pnl_str,
            })
        # Totals row
        t_pnl = f"{'+'if totals['pnl']>=0 else ''}{totals['pnl']:,.2f} ({'+' if totals['pnl_pct']>=0 else ''}{totals['pnl_pct']}%)"
        rows.append({
            "Ticker": "TOTAL", "Shares": "", "Buy Price": "",
            "Current Price": "",
            "Invested": f"${totals['invested']:,.2f}",
            "Value":    f"${totals['current_value']:,.2f}",
            "P&L":      t_pnl,
        })
        df_port = pd.DataFrame(rows)
        st.dataframe(df_port, use_container_width=True, hide_index=True)

# ── TAB 4 : News & Sentiment ─────────────────────────────────────────────────
with tab_news:
    st.markdown(f"### 📰 Latest News — {ticker}")
    with st.spinner("Fetching news…"):
        articles = fetch_news(ticker)

    if not articles:
        st.info(f"No recent news found for **{ticker}**.")
    else:
        for art in articles:
            with st.container():
                st.markdown(f"""
<div style="background:#1e1e2e;border:1px solid #2e2e4e;border-radius:10px;
            padding:14px 18px;margin-bottom:10px;">
  <a href="{art['url']}" target="_blank"
     style="color:#6366f1;font-weight:600;font-size:0.95rem;text-decoration:none;">
    {art['title']}
  </a>
  <p style="color:#9b9bb4;font-size:0.78rem;margin:4px 0 6px;">
    📰 {art['publisher']} &nbsp;·&nbsp; {art['published'][:10] if art['published'] else ''}
  </p>
  <p style="color:#c0c0d0;font-size:0.85rem;margin:0;">{art['summary'][:280]}{'…' if len(art['summary'])>280 else ''}</p>
</div>
""", unsafe_allow_html=True)