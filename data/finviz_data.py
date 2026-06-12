"""
Finviz Elite export API wrapper.
All fetch calls go through _fetch() which enforces a minimum inter-request
delay to stay within Elite rate limits.
"""

import io
import logging
import time
from typing import Optional

import pandas as pd
import requests

import os

from config import FINVIZ_BASE_URL

logger = logging.getLogger(__name__)

_HEADERS = {"User-Agent": "Mozilla/5.0 (PreMarketMovers/1.0)"}
_LAST_CALL: float = 0.0
_MIN_INTERVAL = 1.2   # seconds between requests — stays under Elite rate limit


def _fetch(query_string: str, max_rows: int = 50) -> Optional[pd.DataFrame]:
    """
    Hit the Finviz Elite export endpoint and return a clean DataFrame.
    Returns None on any failure.
    """
    global _LAST_CALL
    elapsed = time.time() - _LAST_CALL
    if elapsed < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - elapsed)
    _LAST_CALL = time.time()

    url = f"{FINVIZ_BASE_URL}?{query_string}&auth={os.environ.get('FINVIZ_API_KEY', '')}"
    try:
        r = requests.get(url, headers=_HEADERS, timeout=15)
        r.raise_for_status()
        if "text/csv" not in r.headers.get("Content-Type", ""):
            logger.warning("Finviz returned non-CSV for %s", query_string)
            return None
        df = pd.read_csv(io.StringIO(r.text))
        return df.head(max_rows)
    except Exception as e:
        logger.error("Finviz fetch error (%s): %s", query_string, e)
        return None


# ── Screener signals ──────────────────────────────────────────────────────────

def get_top_gainers(max_rows: int = 25) -> pd.DataFrame:
    """Top % gainers on the day from Finviz screener."""
    df = _fetch("v=111&s=ta_topgainers", max_rows)
    return df if df is not None else pd.DataFrame()


def get_top_losers(max_rows: int = 25) -> pd.DataFrame:
    """Top % losers on the day from Finviz screener."""
    df = _fetch("v=111&s=ta_toplosers", max_rows)
    return df if df is not None else pd.DataFrame()


def get_unusual_volume(max_rows: int = 25) -> pd.DataFrame:
    """Stocks with unusual volume vs their average."""
    df = _fetch("v=111&s=ta_unusualvolume", max_rows)
    return df if df is not None else pd.DataFrame()


def get_most_active(max_rows: int = 25) -> pd.DataFrame:
    """Most active stocks by total volume traded."""
    df = _fetch("v=111&s=ta_mostactive", max_rows)
    return df if df is not None else pd.DataFrame()


def get_new_highs(max_rows: int = 20) -> pd.DataFrame:
    """Stocks making new 52-week highs — breakout candidates."""
    df = _fetch("v=111&s=ta_newhigh", max_rows)
    return df if df is not None else pd.DataFrame()


def get_new_lows(max_rows: int = 20) -> pd.DataFrame:
    """Stocks making new 52-week lows — breakdown / short candidates."""
    df = _fetch("v=111&s=ta_newlow", max_rows)
    return df if df is not None else pd.DataFrame()


# ── Filtered screeners ────────────────────────────────────────────────────────

def get_earnings_this_week(max_rows: int = 30) -> pd.DataFrame:
    """Liquid stocks reporting earnings this week — high catalyst risk."""
    df = _fetch("v=111&f=earningsdate_thisweek,sh_avgvol_o500", max_rows)
    return df if df is not None else pd.DataFrame()


def get_analyst_upgrades(max_rows: int = 20) -> pd.DataFrame:
    """
    Recent analyst upgrades on liquid stocks (avg vol > 500K).
    Finviz doesn't filter by date alone, so we take the top N by volume
    as a proxy for recency + significance.
    """
    df = _fetch("v=111&f=an_upgrades,sh_avgvol_o500", max_rows=200)
    if df is None or df.empty:
        return pd.DataFrame()
    # Sort by volume desc (highest-profile upgrades first), take top N
    df["Volume_num"] = pd.to_numeric(df["Volume"].astype(str).str.replace(",", ""), errors="coerce")
    df = df.sort_values("Volume_num", ascending=False).head(max_rows).drop(columns=["Volume_num"])
    return df.reset_index(drop=True)


def get_analyst_downgrades(max_rows: int = 20) -> pd.DataFrame:
    """Recent analyst downgrades on liquid stocks, sorted by volume."""
    df = _fetch("v=111&f=an_downgrades,sh_avgvol_o500", max_rows=200)
    if df is None or df.empty:
        return pd.DataFrame()
    df["Volume_num"] = pd.to_numeric(df["Volume"].astype(str).str.replace(",", ""), errors="coerce")
    df = df.sort_values("Volume_num", ascending=False).head(max_rows).drop(columns=["Volume_num"])
    return df.reset_index(drop=True)


def get_insider_buys(max_rows: int = 20) -> pd.DataFrame:
    """
    Mid-cap+ liquid stocks with recent insider buying.
    Filtered to cap_midover + sh_avgvol_o500 to avoid micro-cap noise.
    """
    df = _fetch("v=111&f=n_insiderbuy,cap_midover,sh_avgvol_o500", max_rows)
    return df if df is not None else pd.DataFrame()
