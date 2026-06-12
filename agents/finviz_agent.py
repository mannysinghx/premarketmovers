"""
Finviz Elite Agent — fetches Finviz screener data and uses Claude to
synthesize the signals into a structured market intelligence brief.
"""

from typing import Dict

import pandas as pd

from agents.base_agent import BaseAgent
from data.finviz_data import (
    get_analyst_downgrades,
    get_analyst_upgrades,
    get_earnings_this_week,
    get_insider_buys,
    get_most_active,
    get_new_highs,
    get_new_lows,
    get_top_gainers,
    get_top_losers,
    get_unusual_volume,
)

SYSTEM = """You are a Finviz-powered market intelligence analyst. You receive real-time
screener data across multiple signals (gainers, losers, volume, analyst moves, insiders,
52-week extremes) and synthesize it into an actionable pre-market brief.

Structure your response with these exact section headers:
MARKET TONE: <one-line overall assessment: risk-on/risk-off/mixed>
KEY MOVERS: <3-5 most important stocks from the screener, with a 1-line reason each>
SECTOR THEMES: <dominant sectors appearing across the signals>
INSIDER SIGNAL: <assessment of insider buying pattern — aggressive/moderate/light>
ANALYST FLOW: <net upgrade vs downgrade bias and which sectors are getting revised>
BREAKOUTS: <notable new 52w highs and what they mean for momentum>
WATCH LIST: <5 tickers from the data a trader must watch today, with reason>
RISK FLAGS: <any concerning patterns in the data — volume without price, broad weakness, etc.>"""


def _df_to_lines(df: pd.DataFrame, cols=("Ticker", "Change", "Volume"), max_rows: int = 10) -> str:
    """Compact text representation of a DataFrame for Claude."""
    if df.empty:
        return "(no data)"
    available = [c for c in cols if c in df.columns]
    rows = []
    for _, row in df[available].head(max_rows).iterrows():
        rows.append("  " + "  |  ".join(str(row[c]) for c in available))
    return "\n".join(rows)


class FinvizAgent(BaseAgent):
    def __init__(self):
        super().__init__("FinvizElite", SYSTEM)

    def run(self) -> Dict:
        """
        Fetch all Finviz screener data and return the full intelligence package.

        Returns:
          gainers          — DataFrame
          losers           — DataFrame
          unusual_volume   — DataFrame
          most_active      — DataFrame
          new_highs        — DataFrame
          new_lows         — DataFrame
          earnings_week    — DataFrame
          upgrades         — DataFrame
          downgrades       — DataFrame
          insider_buys     — DataFrame
          analysis         — Claude's structured brief (str)
          watch_list       — parsed list of tickers to watch
        """
        # Fetch all signals — rate limiter in finviz_data.py spaces the calls
        gainers = get_top_gainers()
        losers = get_top_losers()
        unusual_vol = get_unusual_volume()
        most_active = get_most_active()
        new_highs = get_new_highs()
        new_lows = get_new_lows()
        earnings_week = get_earnings_this_week()
        upgrades = get_analyst_upgrades()
        downgrades = get_analyst_downgrades()
        insider = get_insider_buys()

        # Build the brief for Claude
        brief_parts = [
            f"=== TOP GAINERS (Finviz) ===\n{_df_to_lines(gainers)}",
            f"=== TOP LOSERS (Finviz) ===\n{_df_to_lines(losers)}",
            f"=== UNUSUAL VOLUME ===\n{_df_to_lines(unusual_vol)}",
            f"=== MOST ACTIVE ===\n{_df_to_lines(most_active)}",
            f"=== NEW 52-WEEK HIGHS ===\n{_df_to_lines(new_highs)}",
            f"=== NEW 52-WEEK LOWS ===\n{_df_to_lines(new_lows)}",
            f"=== EARNINGS THIS WEEK ===\n{_df_to_lines(earnings_week, cols=('Ticker','Company','Sector','Volume'))}",
            f"=== ANALYST UPGRADES (top by volume) ===\n{_df_to_lines(upgrades, cols=('Ticker','Company','Sector'))}",
            f"=== ANALYST DOWNGRADES (top by volume) ===\n{_df_to_lines(downgrades, cols=('Ticker','Company','Sector'))}",
            f"=== INSIDER BUYING (mid-cap+) ===\n{_df_to_lines(insider, cols=('Ticker','Company','Sector','Volume'))}",
        ]

        prompt = (
            "Here is today's Finviz Elite screener data across all key signals:\n\n"
            + "\n\n".join(brief_parts)
            + "\n\nGenerate the structured market intelligence brief."
        )

        analysis = self.call(prompt, max_tokens=1000)

        # Parse WATCH LIST tickers from response
        watch_list = _parse_watch_list(analysis)

        return {
            "gainers": gainers,
            "losers": losers,
            "unusual_volume": unusual_vol,
            "most_active": most_active,
            "new_highs": new_highs,
            "new_lows": new_lows,
            "earnings_week": earnings_week,
            "upgrades": upgrades,
            "downgrades": downgrades,
            "insider_buys": insider,
            "analysis": analysis,
            "watch_list": watch_list,
        }


def _parse_watch_list(text: str) -> list:
    """Extract tickers from WATCH LIST section."""
    tickers = []
    in_section = False
    for line in text.splitlines():
        if "WATCH LIST:" in line.upper():
            in_section = True
            # tickers might be on the same line
            rest = line.split(":", 1)[-1].strip()
            if rest:
                for word in rest.split():
                    clean = word.strip(".,;()").upper()
                    if 1 <= len(clean) <= 5 and clean.isalpha():
                        tickers.append(clean)
        elif in_section:
            if line.strip().startswith(("RISK", "MARKET", "KEY", "SECTOR", "INSIDER", "ANALYST", "BREAKOUT")):
                break
            for word in line.split():
                clean = word.strip(".,;()").upper()
                if 1 <= len(clean) <= 5 and clean.isalpha() and clean not in {"WITH", "AND", "FOR", "THE", "ARE", "TOP"}:
                    tickers.append(clean)
    return list(dict.fromkeys(tickers))[:8]  # deduplicate, keep order, cap at 8
