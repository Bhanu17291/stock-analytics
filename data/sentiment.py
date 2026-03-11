# data/sentiment.py
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from data.fetcher import fetch_news

# Download vader lexicon if not already present
try:
    nltk.data.find("sentiment/vader_lexicon.zip")
except LookupError:
    nltk.download("vader_lexicon")


def analyze_sentiment(text: str) -> dict:
    """Analyze sentiment of a given text using VADER."""
    sia = SentimentIntensityAnalyzer()
    scores = sia.polarity_scores(text)

    compound = scores["compound"]
    if compound >= 0.05:
        label = "Positive"
        color = "success"
    elif compound <= -0.05:
        label = "Negative"
        color = "danger"
    else:
        label = "Neutral"
        color = "warning"

    return {
        "compound": round(compound, 4),
        "positive": round(scores["pos"], 4),
        "negative": round(scores["neg"], 4),
        "neutral": round(scores["neu"], 4),
        "label": label,
        "color": color,
    }


def get_news_with_sentiment(ticker: str) -> list:
    """Fetch news and attach sentiment scores to each article."""
    news = fetch_news(ticker)

    if not news:
        return []

    results = []
    for article in news:
        text = article.get("title", "") + " " + article.get("summary", "")
        sentiment = analyze_sentiment(text)
        results.append({**article, **sentiment})

    return results


def get_overall_sentiment(ticker: str) -> dict:
    """Get overall sentiment score across all recent news."""
    news = get_news_with_sentiment(ticker)

    if not news:
        return {"label": "No Data", "color": "secondary", "compound": 0, "count": 0}

    avg_compound = sum(a["compound"] for a in news) / len(news)

    if avg_compound >= 0.05:
        label = "Overall Positive"
        color = "success"
    elif avg_compound <= -0.05:
        label = "Overall Negative"
        color = "danger"
    else:
        label = "Overall Neutral"
        color = "warning"

    return {
        "label": label,
        "color": color,
        "compound": round(avg_compound, 4),
        "count": len(news),
    }