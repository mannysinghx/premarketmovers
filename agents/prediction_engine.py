"""
Prediction Engine Agent — synthesizes all agent outputs into actionable
trade setups with directional predictions, key levels, and confidence scores.
"""

from typing import Dict, List

from agents.base_agent import BaseAgent

SYSTEM = """You are a quantitative strategist and trader. You receive a consolidated
intelligence brief from multiple analysis agents (market scan, volume, news, catalysts)
and synthesize it into actionable trade setups.

For each ticker flagged across agents, provide:
- DIRECTION: Bullish / Bearish / Neutral
- CONFIDENCE: 1-10
- THESIS: One-sentence bull or bear case
- TRIGGER: What specific event or level would confirm the move
- RISK: Primary risk to the thesis
- TIMEFRAME: Intraday / Swing (2-5d) / Weekly

Format each prediction as:
TICKER | DIRECTION | CONFIDENCE/10 | TIMEFRAME
  Thesis: ...
  Trigger: ...
  Risk: ...

End with a brief MARKET OUTLOOK section covering overall bias for the session."""


class PredictionEngineAgent(BaseAgent):
    def __init__(self):
        super().__init__("PredictionEngine", SYSTEM)

    def run(self, intelligence_brief: Dict) -> Dict:
        """
        intelligence_brief should contain keys from the orchestrator:
          market_scan, volume_alerts, news_sentiment, catalysts, top_tickers

        Returns:
          predictions  — Claude's raw prediction text
          parsed       — list of parsed prediction dicts (best-effort)
          market_bias  — extracted market outlook string
        """
        # Build the consolidated brief for Claude
        sections = []

        # Market movers section
        if intelligence_brief.get("top_gainers"):
            gainers = ", ".join(
                f"{r['ticker']} (+{r['change_pct']:.1f}%)"
                for r in intelligence_brief["top_gainers"]
            )
            sections.append(f"TOP GAINERS: {gainers}")

        if intelligence_brief.get("top_losers"):
            losers = ", ".join(
                f"{r['ticker']} ({r['change_pct']:.1f}%)"
                for r in intelligence_brief["top_losers"]
            )
            sections.append(f"TOP LOSERS: {losers}")

        # Volume section
        if intelligence_brief.get("volume_alerts"):
            sections.append("VOLUME ALERTS:\n" + "\n".join(intelligence_brief["volume_alerts"][:6]))

        # News sentiment
        sent = intelligence_brief.get("sentiment", {})
        if sent:
            sections.append(
                f"MARKET SENTIMENT: {sent.get('label','?')} ({sent.get('score','?')}/10)"
            )

        # News themes
        if intelligence_brief.get("news_analysis"):
            # Extract just the THEMES line for conciseness
            for line in intelligence_brief["news_analysis"].splitlines():
                if line.startswith("THEMES:") or line.startswith("WATCH:") or line.startswith("CATALYSTS:"):
                    sections.append(line)

        # Near-term catalysts
        if intelligence_brief.get("near_term_catalysts"):
            cats = ", ".join(
                f"{c['ticker']} ({c.get('earnings_days_away','?')}d)"
                for c in intelligence_brief["near_term_catalysts"][:5]
            )
            sections.append(f"EARNINGS THIS WEEK: {cats}")

        # Finviz Elite signals
        if intelligence_brief.get("finviz_watch_list"):
            sections.append(f"FINVIZ WATCH LIST: {', '.join(intelligence_brief['finviz_watch_list'])}")
        if intelligence_brief.get("finviz_analysis"):
            for line in intelligence_brief["finviz_analysis"].splitlines():
                if any(line.startswith(h) for h in ("MARKET TONE:", "SECTOR THEMES:", "INSIDER SIGNAL:", "ANALYST FLOW:", "RISK FLAGS:")):
                    sections.append(f"[FINVIZ] {line}")

        brief = "\n".join(sections)
        prompt = (
            f"Intelligence Brief for {intelligence_brief.get('date','today')}:\n\n"
            f"{brief}\n\n"
            "Generate trade setups and market predictions."
        )

        predictions_text = self.call(prompt, max_tokens=1200)

        # Best-effort parse of predictions
        parsed = _parse_predictions(predictions_text)
        market_bias = _extract_market_outlook(predictions_text)

        return {
            "predictions": predictions_text,
            "parsed": parsed,
            "market_bias": market_bias,
        }


def _parse_predictions(text: str) -> List[Dict]:
    """Extract structured prediction blocks from Claude's response."""
    results = []
    for line in text.splitlines():
        line = line.strip()
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 4 and not line.startswith("MARKET"):
            try:
                conf_raw = parts[2].replace("/10", "").strip()
                conf = int(conf_raw) if conf_raw.isdigit() else 5
                results.append({
                    "ticker": parts[0],
                    "direction": parts[1],
                    "confidence": conf,
                    "timeframe": parts[3],
                })
            except Exception:
                continue
    return results


def _extract_market_outlook(text: str) -> str:
    """Pull the MARKET OUTLOOK section from the prediction text."""
    lines = text.splitlines()
    capturing = False
    outlook_lines = []
    for line in lines:
        if "MARKET OUTLOOK" in line.upper():
            capturing = True
            continue
        if capturing:
            outlook_lines.append(line)
    return "\n".join(outlook_lines).strip() or "See full predictions for market outlook."
