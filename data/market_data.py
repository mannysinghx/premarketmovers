"""
yfinance wrapper — fetches pre-market, volume, fundamentals, and history.
Uses ThreadPoolExecutor so we can scan many tickers without blocking.
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Dict, List, Optional

import pandas as pd
import yfinance as yf

from config import FETCH_WORKERS, SIGNIFICANT_MOVE_PCT, UNUSUAL_VOLUME_MULTIPLIER

logger = logging.getLogger(__name__)


def _fetch_one_mover(ticker: str) -> Optional[Dict]:
    """Fetch price / pre-market movement for a single ticker."""
    try:
        t = yf.Ticker(ticker)
        fi = t.fast_info

        prev_close = getattr(fi, "previous_close", None)
        pre_price = getattr(fi, "pre_market_price", None)
        post_price = getattr(fi, "post_market_price", None)
        last_price = getattr(fi, "last_price", None)

        if prev_close is None:
            return None

        if pre_price:
            price, session = pre_price, "pre-market"
        elif post_price:
            price, session = post_price, "after-hours"
        elif last_price:
            price, session = last_price, "regular"
        else:
            return None

        change = price - prev_close
        change_pct = (change / prev_close) * 100

        vol = getattr(fi, "three_month_average_volume", 0) or 0

        return {
            "ticker": ticker,
            "price": round(price, 2),
            "prev_close": round(prev_close, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "avg_volume": int(vol),
            "session": session,
        }
    except Exception as e:
        logger.debug("Skipping %s: %s", ticker, e)
        return None


def get_movers(tickers: List[str]) -> pd.DataFrame:
    """
    Scan tickers in parallel and return a DataFrame sorted by absolute % change.
    """
    results = []
    with ThreadPoolExecutor(max_workers=FETCH_WORKERS) as pool:
        futures = {pool.submit(_fetch_one_mover, t): t for t in tickers}
        for fut in as_completed(futures):
            res = fut.result()
            if res:
                results.append(res)

    if not results:
        return pd.DataFrame()

    df = pd.DataFrame(results)
    df["abs_change_pct"] = df["change_pct"].abs()
    df = df.sort_values("abs_change_pct", ascending=False).reset_index(drop=True)
    return df


def _fetch_volume_row(ticker: str) -> Optional[Dict]:
    """Fetch volume data + compute ratio vs 90-day average."""
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="3mo", auto_adjust=True)
        if hist.empty:
            return None

        avg_vol = int(hist["Volume"].mean())
        recent_vol = int(hist["Volume"].iloc[-1])
        ratio = recent_vol / avg_vol if avg_vol else 0

        if ratio < UNUSUAL_VOLUME_MULTIPLIER:
            return None  # not interesting

        fi = t.fast_info
        prev_close = getattr(fi, "previous_close", None)
        last_price = getattr(fi, "last_price", None)
        change_pct = 0.0
        if prev_close and last_price:
            change_pct = round((last_price - prev_close) / prev_close * 100, 2)

        return {
            "ticker": ticker,
            "current_volume": recent_vol,
            "avg_volume_90d": avg_vol,
            "volume_ratio": round(ratio, 1),
            "change_pct": change_pct,
        }
    except Exception as e:
        logger.debug("Volume skip %s: %s", ticker, e)
        return None


def get_unusual_volume(tickers: List[str]) -> pd.DataFrame:
    """Return tickers with unusual volume, sorted by ratio descending."""
    results = []
    with ThreadPoolExecutor(max_workers=FETCH_WORKERS) as pool:
        futures = {pool.submit(_fetch_volume_row, t): t for t in tickers}
        for fut in as_completed(futures):
            res = fut.result()
            if res:
                results.append(res)

    if not results:
        return pd.DataFrame()

    df = pd.DataFrame(results)
    return df.sort_values("volume_ratio", ascending=False).reset_index(drop=True)


def get_ticker_info(ticker: str) -> Dict:
    """Full fundamentals + calendar for a single ticker."""
    try:
        t = yf.Ticker(ticker)
        info = t.info
        return {
            "ticker": ticker,
            "name": info.get("longName", ticker),
            "sector": info.get("sector", "Unknown"),
            "industry": info.get("industry", "Unknown"),
            "market_cap": info.get("marketCap", 0),
            "pe_ratio": info.get("trailingPE"),
            "beta": info.get("beta"),
            "short_pct": info.get("shortPercentOfFloat"),
            "analyst_rating": info.get("recommendationKey", "N/A"),
            "target_price": info.get("targetMeanPrice"),
            "earnings_timestamp": info.get("earningsTimestamp"),
            "description": (info.get("longBusinessSummary") or "")[:400],
        }
    except Exception as e:
        logger.debug("Info skip %s: %s", ticker, e)
        return {"ticker": ticker, "name": ticker}


def get_price_history(ticker: str, period: str = "5d", interval: str = "30m") -> pd.DataFrame:
    """OHLCV history including pre/post market for charting."""
    try:
        t = yf.Ticker(ticker)
        df = t.history(period=period, interval=interval, prepost=True, auto_adjust=True)
        return df
    except Exception:
        return pd.DataFrame()
