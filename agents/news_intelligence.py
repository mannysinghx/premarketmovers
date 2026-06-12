"""
News Intelligence Agent — pulls RSS news, runs Claude to extract
catalysts, score sentiment, and surface the top market-moving stories.
"""

from typing import Dict, List

from agents.base_agent import BaseAgent
from data.news_fetcher import fetch_market_news, fetch_ticker_news

SYSTEM = """You are a financial news analyst with expertise in market-moving catalysts.
Given raw news headlines and summaries, you will:
1. Score overall market sentiment: Bullish / Neutral / Bearish (with a 1-10 score, 10=very bullish)
2. Identify the top 3 market themes driving today's news.
3. For each article, extract: catalyst type (earnings, FDA, M&A, macro, legal, product, etc.),
   affected tickers, and expected price impact direction (up/down/neutral).
4. Flag any high-impact events that traders must watch.

Respond in structured plain text. Use these section headers exactly:
SENTIMENT: <score>/10 | <label>
THEMES: <comma-separated themes>
CATALYSTS:
- [TICKER] <catalyst type>: <one-line summary> → <impact>
WATCH: <critical upcoming events>"""


class NewsIntelligenceAgent(BaseAgent):
    def __init__(self):
        super().__init__("NewsIntelligence", SYSTEM)

    def run(self, focus_tickers: List[str] | None = None) -> Dict:
        """
        Returns:
          market_news   — list of raw article dicts
          ticker_news   — dict {ticker: [articles]} for focus tickers
          analysis      — Claude's structured analysis
          sentiment     — parsed sentiment score (int) and label (str)
        """
        # Fetch broad market news
        market_articles = fetch_market_news()

        # Fetch news for the top movers (focus list, up to 8 tickers)
        ticker_news: Dict[str, List] = {}
        if focus_tickers:
            for t in focus_tickers[:8]:
                articles = fetch_ticker_news(t, max_articles=4)
                if articles:
                    ticker_news[t] = articles

        # Build the news corpus for Claude
        lines = []
        for art in market_articles[:10]:
            lines.append(f"[{art['source']}] {art['title']} — {art['summary']}")

        for ticker, arts in ticker_news.items():
            for art in arts[:3]:
                lines.append(f"[{ticker}] {art['title']} — {art['summary']}")

        if not lines:
            return {
                "market_news": [],
                "ticker_news": {},
                "analysis": "No news data available.",
                "sentiment": {"score": 5, "label": "Neutral"},
            }

        corpus = "\n".join(lines)
        prompt = f"Analyze these market news items:\n\n{corpus}"
        analysis = self.call(prompt, max_tokens=900)

        # Parse sentiment from the response
        sentiment = {"score": 5, "label": "Neutral"}
        for line in analysis.splitlines():
            if line.startswith("SENTIMENT:"):
                try:
                    parts = line.replace("SENTIMENT:", "").strip().split("|")
                    score = int(parts[0].strip().split("/")[0])
                    label = parts[1].strip() if len(parts) > 1 else "Neutral"
                    sentiment = {"score": score, "label": label}
                except Exception:
                    pass
                break

        return {
            "market_news": market_articles,
            "ticker_news": ticker_news,
            "analysis": analysis,
            "sentiment": sentiment,
        }
