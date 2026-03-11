# components/news.py
import dash_bootstrap_components as dbc
from dash import html
from data.sentiment import get_news_with_sentiment, get_overall_sentiment


def _sentiment_bar(compound: float) -> html.Div:
    """Render a small visual sentiment bar based on compound score (-1 to 1)."""
    pct        = int((compound + 1) / 2 * 100)   # map -1..1 → 0..100
    if compound >= 0.05:
        color = "#10b981"
    elif compound <= -0.05:
        color = "#f43f5e"
    else:
        color = "#f59e0b"

    return html.Div([
        html.Div(style={
            "width":        f"{pct}%",
            "height":       "3px",
            "background":   color,
            "borderRadius": "2px",
            "transition":   "width 0.4s ease",
        })
    ], style={
        "width":        "60px",
        "height":       "3px",
        "background":   "#1e1e45",
        "borderRadius": "2px",
        "overflow":     "hidden",
        "marginLeft":   "6px",
        "alignSelf":    "center",
    })


def build_news_feed(ticker: str) -> html.Div:
    """Build a news feed with per-article sentiment badges and score bars."""
    try:
        news    = get_news_with_sentiment(ticker)
        overall = get_overall_sentiment(ticker)
    except Exception:
        return html.Div([
            html.Span("⚠️", style={"fontSize": "1.8rem"}),
            html.P("Failed to load news. Please try again.", className="text-muted small mt-2 mb-0"),
        ], className="text-center py-4")

    if not news:
        return html.Div([
            html.Span("📭", style={"fontSize": "1.8rem"}),
            html.P(f"No recent news found for {ticker}.", className="text-muted small mt-2 mb-0"),
        ], className="text-center py-4")

    # ── Overall sentiment banner ──────────────────────────────────────────
    sentiment_icon = {"Positive": "🟢", "Negative": "🔴", "Neutral": "🟡"}.get(
        overall.get("label", "Neutral"), "⚪"
    )
    compound_score = overall.get("compound", 0)
    banner = dbc.Alert(
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.Span(sentiment_icon, style={"fontSize": "1.3rem", "marginRight": "8px"}),
                    html.Span("Overall Sentiment: ", className="text-muted small"),
                    html.Strong(overall.get("label", "N/A")),
                    _sentiment_bar(compound_score),
                ], className="d-flex align-items-center"),
            ], xs=12, md=8),
            dbc.Col([
                html.Small(
                    f"{overall.get('count', 0)} articles · score: {compound_score:+.3f}",
                    className="text-muted"
                ),
            ], xs=12, md=4, className="text-md-end"),
        ], align="center"),
        color=overall.get("color", "secondary"),
        className="mb-3 sentiment-banner",
        style={"borderRadius": "10px"}
    )

    # ── News cards ────────────────────────────────────────────────────────
    cards = []
    for i, article in enumerate(news):
        badge_color = {
            "Positive": "success",
            "Negative": "danger",
            "Neutral":  "warning",
        }.get(article.get("label", "Neutral"), "secondary")

        summary      = article.get("summary", "")
        summary_text = (summary[:220] + "…") if summary and len(summary) > 220 else summary
        art_compound = article.get("compound", 0)

        card = dbc.Card(
            dbc.CardBody([
                # ── Meta row ──
                html.Div([
                    html.Span(
                        article.get("publisher", "Unknown Source"),
                        className="text-muted",
                        style={"fontSize": "0.72rem", "letterSpacing": "0.04em"}
                    ),
                    dbc.Badge(
                        article.get("label", "Neutral"),
                        color=badge_color,
                        className="ms-2",
                        style={"fontSize": "0.65rem"}
                    ),
                    # Inline score + mini bar
                    html.Span(
                        f"{art_compound:+.3f}",
                        className="text-muted ms-2",
                        style={"fontSize": "0.68rem", "fontFamily": "var(--mono)"}
                    ),
                    _sentiment_bar(art_compound),
                ], className="mb-2 d-flex align-items-center flex-wrap"),

                # ── Title ──
                html.H6(
                    html.A(
                        article.get("title", "Untitled"),
                        href=article.get("url", "#"),
                        target="_blank",
                        style={
                            "color":          "#c8c8ff",
                            "textDecoration": "none",
                            "lineHeight":     "1.4",
                            "transition":     "color 0.2s ease",
                        }
                    ),
                    className="mb-1",
                    style={"fontSize": "0.9rem"}
                ),

                # ── Summary ──
                (html.P(
                    summary_text,
                    className="text-muted mb-0",
                    style={"fontSize": "0.78rem", "lineHeight": "1.5"}
                ) if summary_text else None),
            ]),
            className="mb-2 news-card",
            style={"animationDelay": f"{i * 0.05}s"}
        )
        cards.append(card)

    return html.Div([banner] + cards)