# components/charts.py
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from data.fetcher import fetch_stock_data
from data.indicators import get_all_indicators
from config import CHART_THEME


def build_candlestick_chart(ticker: str, period: str = "6mo") -> go.Figure:
    """Build candlestick chart with volume and Bollinger Bands."""
    df = fetch_stock_data(ticker, period)
    if df.empty:
        return go.Figure()

    df = get_all_indicators(df)

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.75, 0.25]
    )

    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df["Open"], high=df["High"],
        low=df["Low"], close=df["Close"],
        name=ticker,
        increasing_line_color="#26a69a",
        decreasing_line_color="#ef5350"
    ), row=1, col=1)

    fig.add_trace(go.Scatter(x=df.index, y=df["BB_Upper"], name="BB Upper",
                             line=dict(color="rgba(173,216,230,0.6)", width=1), showlegend=True), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["BB_Middle"], name="BB Middle",
                             line=dict(color="rgba(255,255,255,0.4)", width=1, dash="dash"), showlegend=True), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["BB_Lower"], name="BB Lower",
                             line=dict(color="rgba(173,216,230,0.6)", width=1),
                             fill="tonexty", fillcolor="rgba(173,216,230,0.05)", showlegend=True), row=1, col=1)

    fig.add_trace(go.Scatter(x=df.index, y=df["EMA_20"], name="EMA 20",
                             line=dict(color="#ff9800", width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["SMA_50"], name="SMA 50",
                             line=dict(color="#ab47bc", width=1.5)), row=1, col=1)

    colors = ["#26a69a" if c >= o else "#ef5350"
              for c, o in zip(df["Close"], df["Open"])]
    fig.add_trace(go.Bar(x=df.index, y=df["Volume"], name="Volume",
                         marker_color=colors, opacity=0.7), row=2, col=1)

    fig.update_layout(
        template=CHART_THEME,
        title=f"{ticker} Price Chart",
        xaxis_rangeslider_visible=False,
        height=600,
        margin=dict(l=40, r=40, t=50, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        paper_bgcolor="#1e1e2e",
        plot_bgcolor="#1e1e2e",
    )

    return fig


def build_rsi_chart(ticker: str, period: str = "6mo") -> go.Figure:
    """Build RSI chart."""
    df = fetch_stock_data(ticker, period)
    if df.empty:
        return go.Figure()

    df = get_all_indicators(df)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    fig = go.Figure()

    fig.add_trace(go.Scatter(x=df.index, y=df["RSI"], name="RSI",
                             line=dict(color="#42a5f5", width=2)))
    fig.add_hline(y=70, line_dash="dash", line_color="#ef5350", annotation_text="Overbought (70)")
    fig.add_hline(y=30, line_dash="dash", line_color="#26a69a", annotation_text="Oversold (30)")
    fig.add_hrect(y0=30, y1=70, fillcolor="rgba(255,255,255,0.03)", line_width=0)

    fig.update_layout(
        template=CHART_THEME,
        title=f"{ticker} RSI (14)",
        height=300,
        yaxis=dict(range=[0, 100]),
        margin=dict(l=40, r=40, t=50, b=40),
        paper_bgcolor="#1e1e2e",
        plot_bgcolor="#1e1e2e",
    )
    return fig


def build_macd_chart(ticker: str, period: str = "6mo") -> go.Figure:
    """Build MACD chart."""
    df = fetch_stock_data(ticker, period)
    if df.empty:
        return go.Figure()

    df = get_all_indicators(df)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    fig = go.Figure()

    colors = ["#26a69a" if v >= 0 else "#ef5350" for v in df["MACD_Hist"]]

    fig.add_trace(go.Bar(x=df.index, y=df["MACD_Hist"], name="Histogram",
                         marker_color=colors, opacity=0.7))
    fig.add_trace(go.Scatter(x=df.index, y=df["MACD"], name="MACD",
                             line=dict(color="#42a5f5", width=2)))
    fig.add_trace(go.Scatter(x=df.index, y=df["MACD_Signal"], name="Signal",
                             line=dict(color="#ff9800", width=2)))

    fig.update_layout(
        template=CHART_THEME,
        title=f"{ticker} MACD",
        height=300,
        margin=dict(l=40, r=40, t=50, b=40),
        paper_bgcolor="#1e1e2e",
        plot_bgcolor="#1e1e2e",
    )
    return fig