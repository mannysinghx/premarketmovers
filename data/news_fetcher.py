"""
Fetches news from RSS feeds (general market) and Yahoo Finance per-ticker feeds.
Returns plain dicts — no AI processing here; that's the news_intelligence agent's job.
"""

import logging
from datetime import datetime
from typing import Dict, List
from email.utils import parsedate_to_datetime

import feedparser
import requests

from config import NEWS_FEEDS, NEWS_MAX_ARTICLES

logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "Mozilla/5.0 (PreMarketMovers/1.0)"}


def _parse_entry(entry: dict, source: str) -> Dict:
    """Normalise a feedparser entry into a clean dict."""
    published = ""
    try:
        published = str(parsedate_to_datetime(entry.get("published", "")))
    except Exception:
        published = entry.get("published", "")

    return {
        "title": entry.get("title", ""),
        "summary": (entry.get("summary") or entry.get("description") or "")[:300],
        "link": entry.get("link", ""),
        "published": published,
        "source": source,
    }


def fetch_market_news() -> List[Dict]:
    """Fetch broad market news from configured RSS feeds."""
    articles = []
    for source, url in NEWS_FEEDS.items():
        try:
            feed = feedparser.parse(url, request_headers=HEADERS)
            for entry in feed.entries[:NEWS_MAX_ARTICLES]:
                articles.append(_parse_entry(entry, source))
        except Exception as e:
            logger.warning("Feed error (%s): %s", source, e)
    return articles


def fetch_ticker_news(ticker: str, max_articles: int = 6) -> List[Dict]:
    """Fetch news for a specific ticker from Yahoo Finance RSS."""
    url = (
        f"https://feeds.finance.yahoo.com/rss/2.0/headline"
        f"?s={ticker}&region=US&lang=en-US"
    )
    articles = []
    try:
        feed = feedparser.parse(url, request_headers=HEADERS)
        for entry in feed.entries[:max_articles]:
            articles.append(_parse_entry(entry, f"Yahoo/{ticker}"))
    except Exception as e:
        logger.warning("Ticker news error (%s): %s", ticker, e)
    return articles


def fetch_news_for_tickers(tickers: List[str]) -> Dict[str, List[Dict]]:
    """Batch-fetch news for multiple tickers. Returns {ticker: [articles]}."""
    result: Dict[str, List[Dict]] = {}
    for ticker in tickers:
        result[ticker] = fetch_ticker_news(ticker, max_articles=4)
    return result
