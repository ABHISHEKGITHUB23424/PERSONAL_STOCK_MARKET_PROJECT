# =============================================================================
# config.py — Central configuration for the Broker Simulation Service
# To swap the data feed (yfinance → KiteTicker), change FEED_MODULE below.
# =============================================================================

import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# ── PostgreSQL ─────────────────────────────────────────────────────────────────
DATABASE_URL = os.environ.get("DATABASE_URL") # E.g., postgresql://user:password@host:port/dbname
DB_HOST     = os.environ.get("DB_HOST", "localhost")
DB_PORT     = int(os.environ.get("DB_PORT", 5432))
DB_NAME     = os.environ.get("DB_NAME", "stock_portfolio")
DB_USER     = os.environ.get("DB_USER", "postgres")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "abhi")

# ── Redis ──────────────────────────────────────────────────────────────────────
REDIS_URL  = os.environ.get("REDIS_URL") # E.g., redis://user:password@host:port/0
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
REDIS_DB   = int(os.environ.get("REDIS_DB", 0))


# ── Feed Selection ─────────────────────────────────────────────────────────────
# "yfinance"  → uses feed/yfinance_feed.py  (mock, current)
# "kite"      → uses feed/kite_feed.py      (real, swap later)
FEED_MODULE = "yfinance"

# ── API Keys ───────────────────────────────────────────────────────────────────
KITE_API_KEY      = "q6da8yqzoo9d05jv"
KITE_API_SECRET   = "rcrer52viaw6llha1olpyxb3u8yg80cz"
MARKETAUX_API_KEY = "69f08093c37334.32177024"
FINNHUB_API_KEY   = "d7o8739r01qmqe7idn70d7o8739r01qmqe7idn7g"
ALPHA_API_KEY     = "DNCJT7J7BAEO78V9"


# ── Simulation Settings ────────────────────────────────────────────────────────
DRIP_INTERVAL_SECONDS = 1      # How fast ticks are pushed (1 tick/sec)
VELOCITY_WINDOW       = 60     # Number of ticks to use for velocity calc

# ── Server ─────────────────────────────────────────────────────────────────────
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 8000
