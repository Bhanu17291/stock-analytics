# components/news.py
import dash_bootstrap_components as dbc
from dash import html
from data.sentiment import get_news_with_sentiment, get_overall_sentiment


def build_news_feed(ticker: str) -> html.Div:
    """Build a news feed with sentiment badges."""
    try:
        news    = get_news_with_sentiment(ticker)
        overall = get_overall_sentiment(ticker)
    except Exception as e:
        return html.Div([
            html.Span("⚠️", style={"fontSize": "1.8rem"}),
            html.P("Failed to load news. Please try again.", className="text-muted small mt-2 mb-0"),
        ], className="text-center py-4")

    if not news:
        return html.Div([
            html.Span("📭", style={"fontSize": "1.8rem"}),
            html.P(f"No recent news found for {ticker}.", className="text-muted small mt-2 mb-0"),
        ], className="text-center py-4")

    # ── Overall sentiment banner ──
    sentiment_icon = {"Positive": "🟢", "Negative": "🔴", "Neutral": "🟡"}.get(overall.get("label", "Neutral"), "⚪")
    banner = dbc.Alert(
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.Span(sentiment_icon, style={"fontSize": "1.3rem", "marginRight": "8px"}),
                    html.Span(f"Overall Sentiment: ", className="text-muted small"),
                    html.Strong(overall.get("label", "N/A")),
                ]),
            ], xs=12, md=8),
            dbc.Col([
                html.Small(
                    f"{overall.get('count', 0)} articles · Compound score: {overall.get('compound', 0)}",
                    className="text-muted"
                ),
            ], xs=12, md=4, className="text-md-end"),
        ], align="center"),
        color=overall.get("color", "secondary"),
        className="mb-3",
        style={"borderRadius": "10px"}
    )

    # ── News cards ──
    cards = []
    for i, article in enumerate(news):
        sentiment_color_map = {"Positive": "success", "Negative": "danger", "Neutral": "warning"}
        badge_color = sentiment_color_map.get(article.get("label", "Neutral"), "secondary")

        summary = article.get("summary", "")
        summary_text = (summary[:220] + "…") if summary and len(summary) > 220 else summary

        card = dbc.Card(
            dbc.CardBody([
                # Meta row
                html.Div([
                    html.Span(article.get("publisher", "Unknown Source"),
                              className="text-muted", style={"fontSize": "0.72rem", "letterSpacing": "0.04em"}),
                    dbc.Badge(article.get("label", "Neutral"), color=badge_color,
                              className="ms-2", style={"fontSize": "0.65rem"}),
                    html.Span(f" · {article.get('compound', 0)}",
                              className="text-muted ms-1", style={"fontSize": "0.72rem"}),
                ], className="mb-2 d-flex align-items-center"),

                # Title
                html.H6(
                    html.A(
                        article.get("title", "Untitled"),
                        href=article.get("url", "#"),
                        target="_blank",
                        style={
                            "color": "#c8c8ff",
                            "textDecoration": "none",
                            "lineHeight": "1.4",
                            "transition": "color 0.2s ease",
                        }
                    ),
                    className="mb-1",
                    style={"fontSize": "0.9rem"}
                ),

                # Summary
                html.P(
                    summary_text or "",
                    className="text-muted mb-0",
                    style={"fontSize": "0.78rem", "lineHeight": "1.5"}
                ) if summary_text else None,
            ]),
            className="mb-2 news-card",
            style={"animationDelay": f"{i * 0.05}s"}
        )
        cards.append(card)

    return html.Div([banner] + cards)