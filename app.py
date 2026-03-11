# app.py
import dash
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
from components.charts import build_candlestick_chart, build_rsi_chart, build_macd_chart
from components.portfolio import add_stock, remove_stock, get_portfolio_summary, get_portfolio_totals
from components.news import build_news_feed
from config import DEFAULT_TICKER, AVAILABLE_PERIODS, DEFAULT_PERIOD, APP_TITLE, APP_PORT, DEBUG

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.CYBORG], title=APP_TITLE, suppress_callback_exceptions=True)

STOCK_OPTIONS = [
    {"label": "🇺🇸 Apple Inc. (AAPL)", "value": "AAPL"},
    {"label": "🇮🇳 Reliance Industries (RELIANCE.BO)", "value": "RELIANCE.BO"},
    {"label": "🇮🇳 Tata Consultancy Services (TCS.BO)", "value": "TCS.BO"},
    {"label": "🇮🇳 HDFC Bank (HDFCBANK.BO)", "value": "HDFCBANK.BO"},
    {"label": "🇮🇳 Infosys (INFY.BO)", "value": "INFY.BO"},
    {"label": "🇮🇳 ICICI Bank (ICICIBANK.BO)", "value": "ICICIBANK.BO"},
    {"label": "🇮🇳 Hindustan Unilever (HINDUNILVR.BO)", "value": "HINDUNILVR.BO"},
    {"label": "🇮🇳 State Bank of India (SBIN.BO)", "value": "SBIN.BO"},
    {"label": "🇮🇳 Bajaj Finance (BAJFINANCE.BO)", "value": "BAJFINANCE.BO"},
    {"label": "🇮🇳 Larsen & Toubro (LT.BO)", "value": "LT.BO"},
    {"label": "🇮🇳 Kotak Mahindra Bank (KOTAKBANK.BO)", "value": "KOTAKBANK.BO"},
]



# ── NAVBAR ───────────────────────────────────────────────────────────────
navbar = dbc.Navbar(
    dbc.Container([
        html.Div([
            html.Span(className="live-dot"),
            html.Span(APP_TITLE, className="navbar-title"),
        ], className="d-flex align-items-center"),
        html.Span("Real-time Market Analytics", className="text-muted small d-none d-md-block"),
    ], fluid=True, className="d-flex justify-content-between align-items-center"),
    className="mb-3 main-navbar",
)

# ── SEARCH BAR ───────────────────────────────────────────────────────────
search_bar = dbc.Card(
    dbc.CardBody([
        dbc.Row([
            dbc.Col(
                dcc.Dropdown(
                    id="stock-quick-select",
                    options=STOCK_OPTIONS,
                    placeholder="⚡ Quick select a stock...",
                    clearable=True,
                    style={"backgroundColor": "#1a1a2e", "color": "#000"}
                ),
                width=12
            ),
        ], className="g-2 mb-2"),
        dbc.Row([
            dbc.Col(
                dbc.Input(
                    id="ticker-input",
                    placeholder="Or type any ticker  (e.g. AAPL, TSLA, RELIANCE.BO...)",
                    value=DEFAULT_TICKER, type="text",
                    className="custom-input"
                ),
                xs=12, sm=12, md=6
            ),
            dbc.Col(
                dcc.Dropdown(
                    id="period-dropdown",
                    options=[{"label": p, "value": p} for p in AVAILABLE_PERIODS],
                    value=DEFAULT_PERIOD, clearable=False,
                    style={"backgroundColor": "#1a1a2e", "color": "#000"}
                ),
                xs=6, sm=6, md=3
            ),
            dbc.Col(
                dbc.Button("🔍 Analyze", id="analyze-btn", color="primary",
                           className="w-100 analyze-btn"),
                xs=6, sm=6, md=3
            ),
        ], className="g-2")
    ]),
    className="mb-3 search-card"
)

# ── TICKER ERROR TOAST ───────────────────────────────────────────────────
error_toast = dbc.Toast(
    id="error-toast",
    header="⚠️ Error",
    is_open=False,
    dismissable=True,
    icon="danger",
    duration=5000,
    style={"position": "fixed", "top": 80, "right": 20, "zIndex": 9999, "minWidth": "280px",
           "backgroundColor": "#1e1e2e", "border": "1px solid #ef5350", "color": "#e0e0e0"}
)

# ── INFO CARDS ───────────────────────────────────────────────────────────
info_cards = dbc.Row(id="info-cards", className="mb-3 g-2")

# ── TABS ─────────────────────────────────────────────────────────────────
tabs = dbc.Tabs([
    dbc.Tab(label="📈 Price Chart",       tab_id="tab-chart"),
    dbc.Tab(label="📊 Indicators",        tab_id="tab-indicators"),
    dbc.Tab(label="💼 Portfolio",         tab_id="tab-portfolio"),
    dbc.Tab(label="📰 News & Sentiment",  tab_id="tab-news"),
], id="tabs", active_tab="tab-chart", className="mb-1")

tab_content = html.Div(id="tab-content")

# ── LAYOUT ───────────────────────────────────────────────────────────────
app.layout = html.Div([
    navbar,
    error_toast,
    dbc.Container([
        search_bar,
        dcc.Loading(
            id="loading-info",
            type="dot",
            color="#6366f1",
            children=info_cards,
        ),
        tabs,
        dcc.Loading(
            id="loading-tab",
            type="circle",
            color="#6366f1",
            children=tab_content,
        ),
    ], fluid=True),
    dcc.Store(id="current-ticker", data=DEFAULT_TICKER),
    dcc.Store(id="current-period", data=DEFAULT_PERIOD),
], style={"backgroundColor": "#0d0d1a", "minHeight": "100vh"})


# ── CALLBACKS ────────────────────────────────────────────────────────────

@app.callback(
    Output("ticker-input", "value"),
    Input("stock-quick-select", "value"),
    prevent_initial_call=True
)
def quick_select_stock(selected):
    return selected if selected else dash.no_update


@app.callback(
    Output("current-ticker", "data"),
    Output("current-period", "data"),
    Output("error-toast", "children"),
    Output("error-toast", "is_open"),
    Input("analyze-btn", "n_clicks"),
    State("ticker-input", "value"),
    State("period-dropdown", "value"),
    prevent_initial_call=True
)
def update_ticker(n_clicks, ticker, period):
    if not ticker or not ticker.strip():
        return dash.no_update, dash.no_update, "Please enter a valid ticker symbol.", True
    clean = ticker.upper().strip()
    return clean, period, "", False


@app.callback(
    Output("info-cards", "children"),
    Input("current-ticker", "data")
)
def update_info_cards(ticker):
    from data.fetcher import fetch_stock_info
    info = fetch_stock_info(ticker)

    if not info:
        return [dbc.Col(html.Div([
            html.Span("⚠️", style={"fontSize": "1.5rem"}),
            html.P(f"Could not load data for '{ticker}'.", className="text-muted small mb-0 mt-1"),
        ], className="error-card"), width=12)]

    def fmt_market_cap(val):
        if not val: return "N/A"
        if val >= 1e12: return f"${val/1e12:.2f}T"
        if val >= 1e9:  return f"${val/1e9:.2f}B"
        if val >= 1e6:  return f"${val/1e6:.2f}M"
        return f"${val:,.0f}"

    price = info.get("current_price", 0)
    currency = info.get("currency", "USD")
    symbol = "₹" if currency == "INR" else "$"

    cards = [
        ("🏢 Company",    info.get("name", ticker)),
        ("💰 Price",      f"{symbol}{price:,.2f}"),
        ("📊 Market Cap", fmt_market_cap(info.get("market_cap", 0))),
        ("📈 52W High",   f"{symbol}{info.get('52w_high', 0):,.2f}"),
        ("📉 52W Low",    f"{symbol}{info.get('52w_low', 0):,.2f}"),
        ("🏭 Sector",     info.get("sector", "N/A")),
    ]

    return [
        dbc.Col(
            dbc.Card(
                dbc.CardBody([
                    html.P(label, className="stat-label mb-1"),
                    html.Div(value, className="stat-value"),
                ]),
                className="stat-card h-100"
            ),
            xs=6, sm=4, md=2,
            className="info-card-col"
        ) for label, value in cards
    ]


@app.callback(
    Output("tab-content", "children"),
    Input("tabs", "active_tab"),
    Input("current-ticker", "data"),
    Input("current-period", "data"),
)
def render_tab(active_tab, ticker, period):

    # ── CHART TAB ──
    if active_tab == "tab-chart":
        fig = build_candlestick_chart(ticker, period)
        if not fig.data:
            return _empty_state(ticker, "price chart")
        return html.Div(dcc.Graph(figure=fig, config={"displayModeBar": True, "responsive": True}),
                        className="chart-wrapper fade-in")

    # ── INDICATORS TAB ──
    elif active_tab == "tab-indicators":
        rsi  = build_rsi_chart(ticker, period)
        macd = build_macd_chart(ticker, period)
        if not rsi.data and not macd.data:
            return _empty_state(ticker, "indicators")
        return html.Div([
            html.Div(dcc.Graph(figure=rsi,  config={"responsive": True}), className="chart-wrapper fade-in"),
            html.Div(dcc.Graph(figure=macd, config={"responsive": True}),
                     className="chart-wrapper fade-in", style={"animationDelay": "0.1s"}),
        ])

    # ── PORTFOLIO TAB ──
    elif active_tab == "tab-portfolio":
        return html.Div([
            dbc.Card(dbc.CardBody([
                html.H5("➕ Manage Portfolio", className="mb-3 text-white fw-semibold"),
                dbc.Row([
                    dbc.Col(dbc.Input(id="p-ticker",  placeholder="Ticker",        type="text",   className="custom-input"), xs=12, sm=6, md=3),
                    dbc.Col(dbc.Input(id="p-shares",  placeholder="Shares",        type="number", className="custom-input"), xs=6,  sm=6, md=3),
                    dbc.Col(dbc.Input(id="p-price",   placeholder="Buy Price",     type="number", className="custom-input"), xs=6,  sm=6, md=3),
                    dbc.Col(dbc.Button("➕ Add",    id="add-stock-btn",    color="success", className="w-100"), xs=6, sm=3, md=2),
                    dbc.Col(dbc.Button("🗑️ Remove", id="remove-stock-btn", color="danger",  className="w-100"), xs=6, sm=3, md=1),
                ], className="g-2"),
                html.Div(id="portfolio-msg", className="mt-2"),
            ]), className="mb-3 portfolio-add-card"),
            html.Div(id="portfolio-table"),
        ], className="fade-in")

    # ── NEWS TAB ──
    elif active_tab == "tab-news":
        return html.Div([
            html.H5(f"📰 Latest News — {ticker}", className="text-white mb-3 fw-semibold"),
            build_news_feed(ticker),
        ], className="fade-in")


@app.callback(
    Output("portfolio-msg",   "children"),
    Output("portfolio-table", "children"),
    Input("add-stock-btn",    "n_clicks"),
    Input("remove-stock-btn", "n_clicks"),
    State("p-ticker", "value"),
    State("p-shares", "value"),
    State("p-price",  "value"),
    prevent_initial_call=True
)
def update_portfolio(add_clicks, remove_clicks, ticker, shares, price):
    from dash import ctx
    msg = ""
    if ctx.triggered_id == "add-stock-btn":
        if not ticker or not shares or not price:
            msg = dbc.Alert("⚠️ Please fill in all fields before adding.", color="warning",
                            dismissable=True, duration=4000)
        else:
            try:
                add_stock(ticker, float(shares), float(price))
                msg = dbc.Alert(f"✅ {ticker.upper()} added to portfolio!", color="success",
                                dismissable=True, duration=3000)
            except Exception as e:
                msg = dbc.Alert(f"❌ Failed to add stock: {str(e)}", color="danger",
                                dismissable=True, duration=5000)
    elif ctx.triggered_id == "remove-stock-btn":
        if not ticker:
            msg = dbc.Alert("⚠️ Enter a ticker symbol to remove.", color="warning",
                            dismissable=True, duration=4000)
        else:
            try:
                remove_stock(ticker)
                msg = dbc.Alert(f"🗑️ {ticker.upper()} removed from portfolio.", color="secondary",
                                dismissable=True, duration=3000)
            except Exception as e:
                msg = dbc.Alert(f"❌ Failed to remove stock: {str(e)}", color="danger",
                                dismissable=True, duration=5000)

    return msg, _build_portfolio_table()


# ── HELPERS ──────────────────────────────────────────────────────────────

def _empty_state(ticker: str, section: str) -> html.Div:
    """Shown when data fetch fails."""
    return html.Div([
        html.Span("📭", style={"fontSize": "2.5rem"}),
        html.H5(f"No data available for '{ticker}'", className="text-white mt-3 mb-1"),
        html.P(f"Could not load {section}. Check the ticker symbol and try again.",
               className="text-muted small"),
    ], className="error-card text-center py-5 fade-in")


def _build_portfolio_table() -> html.Div:
    summary = get_portfolio_summary()
    totals  = get_portfolio_totals()

    if not summary:
        return dbc.Alert([
            html.Span("💼 ", style={"fontSize": "1.2rem"}),
            "Your portfolio is empty. Add stocks above to get started.",
        ], color="secondary", className="fade-in")

    rows = [
        html.Tr([
            html.Td(html.Span(s["ticker"], className="fw-bold text-white")),
            html.Td(s["shares"]),
            html.Td(f"${s['buy_price']:,.2f}"),
            html.Td(f"${s['current_price']:,.2f}"),
            html.Td(f"${s['invested']:,.2f}"),
            html.Td(f"${s['current_value']:,.2f}"),
            html.Td(html.Span(
                f"{'+'if s['pnl']>=0 else ''}{s['pnl']:,.2f} ({s['pnl_pct']}%)",
                className=f"text-{'success' if s['pnl']>=0 else 'danger'} fw-bold"
            )),
        ]) for s in summary
    ]

    total_row = html.Tr([
        html.Td("TOTAL", colSpan=4, className="fw-bold text-white"),
        html.Td(f"${totals['invested']:,.2f}",     className="fw-bold"),
        html.Td(f"${totals['current_value']:,.2f}", className="fw-bold"),
        html.Td(html.Span(
            f"{'+'if totals['pnl']>=0 else ''}{totals['pnl']:,.2f} ({totals['pnl_pct']}%)",
            className=f"text-{'success' if totals['pnl']>=0 else 'danger'} fw-bold"
        )),
    ], style={"borderTop": "2px solid #4a4a6e"})

    return dbc.Table(
        [
            html.Thead(html.Tr([
                html.Th(h) for h in
                ["Ticker", "Shares", "Buy Price", "Current", "Invested", "Value", "P&L"]
            ])),
            html.Tbody(rows + [total_row]),
        ],
        bordered=True, hover=True, responsive=True, striped=True,
        className="portfolio-table fade-in",
        style={"color": "#e0e0e0"}
    )


server = app.server  # Required for gunicorn

if __name__ == "__main__":
    app.run(debug=DEBUG, port=APP_PORT, host="0.0.0.0")