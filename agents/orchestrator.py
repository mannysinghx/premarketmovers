"""
Orchestrator — runs all agents in the optimal order and assembles
a unified intelligence package for the Streamlit dashboard.
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Dict, List

from agents.catalyst_detector import CatalystDetectorAgent
from agents.finviz_agent import FinvizAgent
from agents.market_scanner import MarketScannerAgent
from agents.news_intelligence import NewsIntelligenceAgent
from agents.prediction_engine import PredictionEngineAgent
from agents.volume_analyzer import VolumeAnalyzerAgent
import os

from config import SCAN_UNIVERSE

logger = logging.getLogger(__name__)


class IntelligenceOrchestrator:
    """
    Runs the agent pipeline and returns a unified intelligence dict.

    Pipeline:
    1. MarketScanner + VolumeAnalyzer  — parallel (data-only)
    2. NewsIntelligence                — needs top movers as focus list
    3. CatalystDetector                — independent
    4. PredictionEngine                — needs all prior results
    """

    def __init__(self, tickers: List[str] | None = None):
        self.tickers = tickers or SCAN_UNIVERSE
        self.scanner = MarketScannerAgent()
        self.volume = VolumeAnalyzerAgent()
        self.news = NewsIntelligenceAgent()
        self.catalysts = CatalystDetectorAgent()
        self.predictor = PredictionEngineAgent()
        self.finviz = FinvizAgent() if os.environ.get("FINVIZ_API_KEY") else None

    def run(self, progress_callback=None) -> Dict:
        """
        Execute the full pipeline and return the intelligence package.
        progress_callback(step: str, pct: int) is called if provided.
        """
        def _progress(msg, pct):
            if progress_callback:
                progress_callback(msg, pct)
            logger.info("[%d%%] %s", pct, msg)

        result = {}

        # ── Phase 1: Finviz Elite screener (runs first — independent, no ticker list needed) ──
        _progress("Fetching Finviz Elite screener data…", 5)
        finviz_result = {}
        if self.finviz:
            try:
                finviz_result = self.finviz.run()
            except Exception as e:
                logger.error("Finviz agent error: %s", e)
        result["finviz"] = finviz_result

        # ── Phase 2: Market scan + volume (parallel) ──────────────────────
        _progress("Scanning pre-market movers and volume anomalies…", 25)

        scan_result = {}
        vol_result = {}

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = {
                pool.submit(self.scanner.run, self.tickers): "scan",
                pool.submit(self.volume.run, self.tickers): "volume",
            }
            for fut in as_completed(futures):
                key = futures[fut]
                try:
                    if key == "scan":
                        scan_result = fut.result()
                    else:
                        vol_result = fut.result()
                except Exception as e:
                    logger.error("%s agent error: %s", key, e)

        result["market_scan"] = scan_result
        result["volume"] = vol_result

        # Derive top tickers list for subsequent agents
        top_tickers = []
        if not scan_result.get("gainers", None) is None and not scan_result["gainers"].empty:
            top_tickers += scan_result["gainers"]["ticker"].tolist()[:5]
        if not scan_result.get("losers", None) is None and not scan_result["losers"].empty:
            top_tickers += scan_result["losers"]["ticker"].tolist()[:5]

        _progress("Running news intelligence…", 50)

        # ── Phase 2: News (sequential — needs top tickers) ─────────────────
        try:
            news_result = self.news.run(focus_tickers=top_tickers)
        except Exception as e:
            logger.error("News agent error: %s", e)
            news_result = {"market_news": [], "ticker_news": {}, "analysis": str(e), "sentiment": {"score": 5, "label": "Neutral"}}
        result["news"] = news_result

        # ── Phase 3: Catalysts (can run alongside news in theory, but shares API) ──
        _progress("Detecting catalysts and events…", 70)
        try:
            catalyst_result = self.catalysts.run(top_tickers or self.tickers[:20])
        except Exception as e:
            logger.error("Catalyst agent error: %s", e)
            catalyst_result = {"catalysts": [], "analysis": str(e), "near_term": []}
        result["catalysts"] = catalyst_result

        # ── Phase 4: Predictions (needs everything above) ──────────────────
        _progress("Generating AI predictions…", 85)

        # Build the brief
        top_gainers = scan_result.get("gainers", None)
        top_losers = scan_result.get("losers", None)
        brief = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "top_gainers": top_gainers.to_dict("records") if top_gainers is not None and not top_gainers.empty else [],
            "top_losers": top_losers.to_dict("records") if top_losers is not None and not top_losers.empty else [],
            "volume_alerts": vol_result.get("alerts", []),
            "sentiment": news_result.get("sentiment", {}),
            "news_analysis": news_result.get("analysis", ""),
            "near_term_catalysts": catalyst_result.get("near_term", []),
            "finviz_watch_list": finviz_result.get("watch_list", []),
            "finviz_analysis": finviz_result.get("analysis", ""),
        }

        try:
            pred_result = self.predictor.run(brief)
        except Exception as e:
            logger.error("Prediction agent error: %s", e)
            pred_result = {"predictions": str(e), "parsed": [], "market_bias": ""}
        result["predictions"] = pred_result

        _progress("Intelligence package ready.", 100)
        result["generated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S ET")
        return result
