"""
Catalyst Detector Agent — surfaces upcoming earnings, ex-dividend dates,
analyst events, and macro releases that could move stocks.
"""

from datetime import datetime, timezone
from typing import Dict, List

import yfinance as yf

from agents.base_agent import BaseAgent

SYSTEM = """You are an event-driven trading analyst. Given a list of tickers with
their upcoming earnings dates, analyst ratings, and key fundamental data, you will:
1. Rank tickers by catalyst importance (high/medium/low).
2. For each ticker with a near-term catalyst, explain the setup: why traders should watch it,
   what the bull and bear cases are, and what kind of move to expect.
3. Flag any tickers in a pre-earnings squeeze pattern (elevated IV, high short interest).
4. Mention any sector-wide macro events (FOMC, CPI, earnings season themes) relevant to
   the watchlist.

Be analytical and specific. Use plain text. One block per ticker."""


def _days_until(timestamp) -> int | None:
    """Convert an earnings Unix timestamp to days from now."""
    try:
        ts = int(timestamp)
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        delta = dt - datetime.now(tz=timezone.utc)
        return delta.days
    except Exception:
        return None


def _fetch_catalyst_data(ticker: str) -> Dict:
    """Pull key catalyst info for one ticker."""
    try:
        t = yf.Ticker(ticker)
        info = t.info

        earnings_ts = info.get("earningsTimestamp")
        days_to_earnings = _days_until(earnings_ts) if earnings_ts else None

        return {
            "ticker": ticker,
            "name": info.get("shortName", ticker),
            "sector": info.get("sector", "Unknown"),
            "earnings_days_away": days_to_earnings,
            "analyst_rating": info.get("recommendationKey", "N/A"),
            "target_price": info.get("targetMeanPrice"),
            "short_pct": info.get("shortPercentOfFloat"),
            "iv_percentile": None,  # yfinance doesn't expose this; would need options chain
            "pe_ratio": info.get("trailingPE"),
            "revenue_growth": info.get("revenueGrowth"),
        }
    except Exception:
        return {"ticker": ticker, "name": ticker}


class CatalystDetectorAgent(BaseAgent):
    def __init__(self):
        super().__init__("CatalystDetector", SYSTEM)

    def run(self, tickers: List[str]) -> Dict:
        """
        Returns:
          catalysts    — list of catalyst dicts, sorted by days_to_earnings
          analysis     — Claude's event-driven analysis
          near_term    — tickers with earnings within 7 days
        """
        raw = [_fetch_catalyst_data(t) for t in tickers[:30]]  # cap for speed

        # Sort by nearness of earnings (None goes last)
        raw.sort(key=lambda x: (x.get("earnings_days_away") is None, x.get("earnings_days_away") or 999))

        near_term = [r for r in raw if r.get("earnings_days_away") is not None and r["earnings_days_away"] <= 7]

        # Build summary for Claude
        lines = []
        for r in raw[:20]:
            days = r.get("earnings_days_away")
            days_str = f"earnings in {days}d" if days is not None else "no upcoming earnings"
            short = f"{r.get('short_pct', 0) or 0:.1%}" if r.get("short_pct") else "N/A"
            lines.append(
                f"{r['ticker']} ({r.get('sector','?')}): {days_str} | "
                f"analyst={r.get('analyst_rating','N/A')} | short={short} | "
                f"target=${r.get('target_price','N/A')}"
            )

        prompt = (
            f"Today is {datetime.now().strftime('%Y-%m-%d')}. "
            f"Here is the catalyst calendar for the watchlist:\n\n"
            + "\n".join(lines)
            + "\n\nProvide your event-driven analysis."
        )
        analysis = self.call(prompt, max_tokens=900)

        return {
            "catalysts": raw,
            "analysis": analysis,
            "near_term": near_term,
        }
