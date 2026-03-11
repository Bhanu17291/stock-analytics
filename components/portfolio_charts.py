# components/portfolio_charts.py
"""
Portfolio-specific charts:
  - build_allocation_chart  : pie chart of current value by ticker
  - build_pnl_history_chart : line chart of portfolio value over time
"""
import logging

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from components.portfolio import get_portfolio_summary, get_portfolio_history
from config import CHART_THEME

logger = logging.getLogger(__name__)

# Colour palette that matches the existing dark theme
_PALETTE = [
    "#6366f1", "#8b5cf6", "#a78bfa", "#10b981",
    "#f59e0b", "#f43f5e", "#38bdf8", "#fb923c",
    "#34d399", "#e879f9",
]

_LAYOUT_BASE = dict(
    template=CHART_THEME,
    paper_bgcolor="#1e1e2e",
    plot_bgcolor="#1e1e2e",
    font=dict(color="#eeeeff", family="Outfit, sans-serif"),
    margin=dict(l=40, r=40, t=55, b=40),
)


def build_allocation_chart() -> go.Figure:
    """
    Donut chart showing each ticker's share of the total portfolio value.
    Returns an empty Figure if the portfolio is empty.
    """
    summary = get_portfolio_summary()
    if not summary:
        return go.Figure()

    labels = [s["ticker"]        for s in summary]
    values = [s["current_value"] for s in summary]

    # Filter out zero-value positions
    pairs  = [(l, v) for l, v in zip(labels, values) if v > 0]
    if not pairs:
        return go.Figure()
    labels, values = zip(*pairs)

    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.55,
        marker=dict(
            colors=_PALETTE[:len(labels)],
            line=dict(color="#1e1e2e", width=2),
        ),
        textinfo="label+percent",
        textfont=dict(size=13, family="JetBrains Mono, monospace"),
        hovertemplate="<b>%{label}</b><br>Value: $%{value:,.2f}<br>Share: %{percent}<extra></extra>",
        pull=[0.04] * len(labels),
    ))

    # Centre annotation
    total = sum(values)
    fig.add_annotation(
        text=f"<b>${total:,.0f}</b><br><span style='font-size:11px;color:#6b6b9a'>Total Value</span>",
        x=0.5, y=0.5,
        font=dict(size=16, color="#eeeeff", family="JetBrains Mono, monospace"),
        showarrow=False,
    )

    fig.update_layout(
        **_LAYOUT_BASE,
        title=dict(text="Portfolio Allocation", font=dict(size=15)),
        legend=dict(
            orientation="v",
            x=1.02, y=0.5,
            font=dict(size=12),
        ),
        height=380,
    )
    return fig


def build_pnl_history_chart() -> go.Figure:
    """
    Line chart of portfolio value + invested cost over time,
    with a shaded P&L area between them.
    Returns an empty Figure if fewer than 2 snapshots exist.
    """
    history = get_portfolio_history()
    if len(history) < 2:
        return go.Figure()

    dates         = [h["date"]          for h in history]
    values        = [h["current_value"] for h in history]
    invested      = [h["invested"]      for h in history]
    pnl_vals      = [h["pnl"]           for h in history]

    is_positive   = pnl_vals[-1] >= 0
    area_color    = "rgba(16,185,129,0.12)"  if is_positive else "rgba(244,63,94,0.12)"
    line_color    = "#10b981"                if is_positive else "#f43f5e"

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.06,
        row_heights=[0.68, 0.32],
    )

    # ── Value area ──
    fig.add_trace(go.Scatter(
        x=dates, y=values,
        name="Portfolio Value",
        line=dict(color=line_color, width=2.5),
        fill="tonexty",
        fillcolor=area_color,
        hovertemplate="<b>%{x}</b><br>Value: $%{y:,.2f}<extra></extra>",
    ), row=1, col=1)

    # ── Invested cost baseline ──
    fig.add_trace(go.Scatter(
        x=dates, y=invested,
        name="Amount Invested",
        line=dict(color="#6366f1", width=1.5, dash="dot"),
        hovertemplate="<b>%{x}</b><br>Invested: $%{y:,.2f}<extra></extra>",
    ), row=1, col=1)

    # ── P&L bars ──
    bar_colors = [
        "#10b981" if p >= 0 else "#f43f5e"
        for p in pnl_vals
    ]
    fig.add_trace(go.Bar(
        x=dates, y=pnl_vals,
        name="Daily P&L",
        marker_color=bar_colors,
        opacity=0.75,
        hovertemplate="<b>%{x}</b><br>P&L: $%{y:,.2f}<extra></extra>",
    ), row=2, col=1)

    # Zero line on P&L panel
    fig.add_hline(y=0, line_dash="dash", line_color="#252550", row=2, col=1)

    fig.update_layout(
        **_LAYOUT_BASE,
        title=dict(text="Portfolio Value Over Time", font=dict(size=15)),
        height=480,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis2=dict(showgrid=False),
        yaxis=dict( gridcolor="#1a1a3a", tickprefix="$"),
        yaxis2=dict(gridcolor="#1a1a3a", tickprefix="$", title="P&L"),
    )
    return fig