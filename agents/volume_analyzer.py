"""
Volume Analyzer Agent — detects unusual volume spikes and uses Claude
to assess what the abnormal activity might signal.
"""

from typing import Dict, List

from agents.base_agent import BaseAgent
from config import EXTREME_VOLUME_MULTIPLIER, SCAN_UNIVERSE, UNUSUAL_VOLUME_MULTIPLIER
from data.market_data import get_unusual_volume

SYSTEM = """You are a market microstructure analyst specializing in volume analysis.
Given stocks with abnormal volume vs their 90-day average, explain:
- What the volume spike likely signals (institutional accumulation, retail FOMO,
  options-related hedging, earnings whisper, short covering, etc.)
- Whether the price action confirms or contradicts the volume story.
- Risk level: High / Medium / Low for chasing the move.

Be direct and data-driven. No markdown headers. One paragraph per ticker."""


class VolumeAnalyzerAgent(BaseAgent):
    def __init__(self):
        super().__init__("VolumeAnalyzer", SYSTEM)

    def run(self, tickers: List[str] | None = None) -> Dict:
        """
        Returns:
          volume_df  — DataFrame of unusual-volume stocks
          analysis   — Claude's interpretation
          alerts     — list of high-priority alert strings
        """
        tickers = tickers or SCAN_UNIVERSE
        df = get_unusual_volume(tickers)

        if df.empty:
            return {"volume_df": df, "analysis": "No unusual volume detected.", "alerts": []}

        # Build alerts list
        alerts = []
        for _, row in df.iterrows():
            if row["volume_ratio"] >= EXTREME_VOLUME_MULTIPLIER:
                tag = "🔴 EXTREME"
            else:
                tag = "🟡 UNUSUAL"
            alerts.append(
                f"{tag} {row['ticker']}: {row['volume_ratio']:.1f}x avg vol  |  {row['change_pct']:+.2f}%"
            )

        # Prompt Claude with top 8 volume anomalies
        top = df.head(8)
        rows = []
        for _, r in top.iterrows():
            rows.append(
                f"{r['ticker']}: {r['volume_ratio']:.1f}x avg  |  price chg {r['change_pct']:+.2f}%  "
                f"| cur vol {r['current_volume']:,}  | avg vol {r['avg_volume_90d']:,}"
            )
        table = "\n".join(rows)

        prompt = (
            f"These stocks are showing unusual volume today:\n\n{table}\n\n"
            "Analyze each and explain what the volume story is telling us."
        )
        analysis = self.call(prompt, max_tokens=700)

        return {"volume_df": df, "analysis": analysis, "alerts": alerts}
