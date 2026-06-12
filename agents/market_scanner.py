"""
Market Scanner Agent — finds top pre-market movers and asks Claude
to explain the likely driver and rate the momentum quality.
"""

from typing import Dict, List

import pandas as pd

from agents.base_agent import BaseAgent
from config import SCAN_UNIVERSE
from data.market_data import get_movers

SYSTEM = """You are a pre-market equity analyst. Given a list of stocks with their
pre-market price change, your job is to:
1. Identify the most noteworthy movers (top gainers and losers).
2. Briefly explain the likely driver for each move (earnings beat/miss, news catalyst,
   sector rotation, macro event, momentum continuation, or short squeeze).
3. Rate momentum quality: Strong / Moderate / Weak based on context.

Be concise — one or two sentences per ticker. Use plain text, no markdown headers."""


class MarketScannerAgent(BaseAgent):
    def __init__(self):
        super().__init__("MarketScanner", SYSTEM)

    def run(self, tickers: List[str] | None = None) -> Dict:
        """
        Returns:
          movers_df  — full DataFrame of all scanned tickers
          gainers    — top 10 gainers
          losers     — top 10 losers
          analysis   — Claude's narrative commentary
        """
        tickers = tickers or SCAN_UNIVERSE
        df = get_movers(tickers)

        if df.empty:
            return {"movers_df": df, "gainers": pd.DataFrame(), "losers": pd.DataFrame(), "analysis": "No data available."}

        gainers = df[df["change_pct"] > 0].head(10)
        losers = df[df["change_pct"] < 0].tail(10).iloc[::-1]

        # Build a compact table for Claude
        top_rows = pd.concat([gainers.head(5), losers.head(5)])
        table_lines = []
        for _, row in top_rows.iterrows():
            sign = "+" if row["change_pct"] > 0 else ""
            table_lines.append(
                f"{row['ticker']}: {sign}{row['change_pct']:.2f}%  (${row['price']})  [{row['session']}]"
            )
        table_str = "\n".join(table_lines)

        prompt = (
            f"Today's top pre-market movers (session type noted in brackets):\n\n"
            f"{table_str}\n\n"
            "Provide a brief analyst commentary on the notable movers."
        )
        analysis = self.call(prompt, max_tokens=600)

        return {
            "movers_df": df,
            "gainers": gainers,
            "losers": losers,
            "analysis": analysis,
        }
