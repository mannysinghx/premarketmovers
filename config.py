import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MODEL = "claude-sonnet-4-6"

# Curated high-profile tickers across key sectors
SCAN_UNIVERSE = [
    # Mega-cap tech
    "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA",
    # Semiconductors
    "AMD", "INTC", "QCOM", "AVGO", "MU", "SMCI", "ARM", "MRVL",
    # AI / Cloud
    "PLTR", "SNOW", "DDOG", "NET", "AI", "SOUN", "PATH",
    # Financials
    "JPM", "GS", "BAC", "WFC", "MS", "C", "V", "MA", "PYPL", "SQ",
    # Healthcare / Biotech
    "JNJ", "PFE", "MRNA", "BNTX", "ABBV", "LLY", "BMY", "GILD",
    "SAVA", "NVAX", "SRPT",
    # Energy
    "XOM", "CVX", "OXY", "SLB", "MPC",
    # Consumer
    "WMT", "COST", "TGT", "HD", "NKE",
    # EV / Auto
    "RIVN", "LCID", "F", "GM", "NIO", "XPEV", "LI",
    # Crypto-related
    "COIN", "MARA", "RIOT", "HUT", "CLSK",
    # Popular retail
    "GME", "AMC", "BB",
    # ETFs (for market context)
    "SPY", "QQQ", "IWM", "TQQQ", "SOXL", "UVXY",
    # Chinese ADRs
    "BABA", "JD", "PDD", "BIDU",
    # Other high-movers
    "UBER", "LYFT", "ABNB", "DASH", "RBLX", "SNAP", "PINS",
]

SCAN_UNIVERSE = list(dict.fromkeys(SCAN_UNIVERSE))  # deduplicate, preserve order

# News RSS feeds
NEWS_FEEDS = {
    "Yahoo Finance": "https://feeds.finance.yahoo.com/rss/2.0/headline?region=US&lang=en-US",
    "MarketWatch": "https://feeds.marketwatch.com/marketwatch/topstories/",
}

# Thresholds
UNUSUAL_VOLUME_MULTIPLIER = 2.0
EXTREME_VOLUME_MULTIPLIER = 5.0
SIGNIFICANT_MOVE_PCT = 2.0      # % move considered significant pre-market

# Performance
FETCH_WORKERS = 10              # Threads for parallel yfinance requests
NEWS_MAX_ARTICLES = 8           # Articles per AI news summary
