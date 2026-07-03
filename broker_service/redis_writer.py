# =============================================================================
# redis_writer.py — Tick storage with Redis TimeSeries + In-Memory Fallback
#
# Strategy:
#   1. Try to connect to Redis on startup.
#   2. If Redis is available  → use TS.ADD / TS.REVRANGE (proper time-series).
#   3. If Redis is NOT found  → fall back to a thread-safe in-memory deque.
#      Everything else in the system (velocity, WebSocket) works identically.
#
# Install Redis later (optional):
#   Windows: https://github.com/microsoftarchive/redis/releases
#            OR via WSL: sudo apt install redis-server && redis-server
# =============================================================================

import time
import asyncio
import collections
import threading
from typing import List, Optional, Dict, Any
import config

# ── In-memory fallback store ──────────────────────────────────────────────────
# { "AAPL": deque([(timestamp_ms, price, volume), ...], maxlen=600) }
_memory_store: dict = {}
_memory_lock  = threading.Lock()
_use_redis    = False          # Set to True if Redis connects successfully

# ── Try to import Redis ────────────────────────────────────────────────────────
try:
    import redis as redis_lib
    _redis_available = True
except ImportError:
    _redis_available = False


def _make_redis_client():
    """Return a Redis client, or None if unavailable."""
    if not _redis_available:
        return None
    try:
        if config.REDIS_URL:
            client = redis_lib.Redis.from_url(
                config.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=1,   # Fast fail — don't hang
            )
        else:
            client = redis_lib.Redis(
                host=config.REDIS_HOST,
                port=config.REDIS_PORT,
                db=config.REDIS_DB,
                decode_responses=True,
                socket_connect_timeout=1,   # Fast fail — don't hang
            )
        client.ping()                   # Actual connection check
        return client
    except Exception:
        return None



def _check_redis() -> bool:
    """Check once at startup whether Redis is reachable."""
    global _use_redis
    client = _make_redis_client()
    if client:
        _use_redis = True
        print("[Storage] SUCCESS: Redis is reachable - using Redis TimeSeries")
    else:
        _use_redis = False
        print("[Storage] WARNING: Redis not found - using in-memory deque (works fine!)")
        print("[Storage]   To use Redis later: install Redis and restart main.py")
    return _use_redis


# Run the check immediately when module loads
_check_redis()


# ── Public API (same interface regardless of backend) ─────────────────────────

def get_redis_client() -> Optional[object]:
    """Return a live Redis client if available, otherwise None."""
    if _use_redis:
        return _make_redis_client()
    return None


def create_timeseries_key(client, ticker: str):
    """Create Redis TS key if using Redis; set up memory bucket otherwise."""
    if _use_redis and client:
        key_price = f"price:{ticker}"
        key_vol = f"volume:{ticker}"
        try:
            client.execute_command(
                "TS.CREATE", key_price, "RETENTION", 600000,
                "LABELS", "ticker", ticker, "type", "price"
            )
            client.execute_command(
                "TS.CREATE", key_vol, "RETENTION", 600000,
                "LABELS", "ticker", ticker, "type", "volume"
            )
        except Exception as e:
            if "key already exists" not in str(e).lower():
                raise
    else:
        with _memory_lock:
            if ticker not in _memory_store:
                # maxlen=600 keeps the last 10 minutes at 1 tick/sec
                _memory_store[ticker] = collections.deque(maxlen=600)


def push_tick(client, ticker: str, price: float, volume: int):
    """Push one price and volume tick to Redis TS or the in-memory deque."""
    ts_ms = int(time.time() * 1000)  # millisecond timestamp

    if _use_redis and client:
        key_price = f"price:{ticker}"
        key_vol = f"volume:{ticker}"
        client.execute_command("TS.ADD", key_price, "*", price)
        client.execute_command("TS.ADD", key_vol, "*", volume)
    else:
        with _memory_lock:
            if ticker not in _memory_store:
                _memory_store[ticker] = collections.deque(maxlen=600)
            _memory_store[ticker].append((ts_ms, price, volume))


def get_last_n_ticks(client, ticker: str, n: int) -> List[Dict[str, float]]:
    """
    Retrieve the last N ticks, oldest → newest.
    Works with both Redis and in-memory backend.
    """
    if _use_redis and client:
        key_price = f"price:{ticker}"
        key_vol = f"volume:{ticker}"
        try:
            p_results = client.execute_command("TS.REVRANGE", key_price, "-", "+", "COUNT", n)
            v_results = client.execute_command("TS.REVRANGE", key_vol, "-", "+", "COUNT", n)
            
            combined = []
            for p_entry, v_entry in zip(p_results, v_results):
                combined.append({
                    "price": float(p_entry[1]),
                    "volume": float(v_entry[1])
                })
            combined.reverse()
            return combined
        except Exception:
            return []
    else:
        with _memory_lock:
            store = _memory_store.get(ticker, collections.deque())
            items = list(store)          # oldest → newest (deque order)
            return [{"price": p, "volume": v} for _, p, v in items[-n:]]


async def drip_feed(ticker: str, ticks: List[Dict[str, Any]], active_tickers: dict):
    """
    Drip-feed coroutine: pushes one tick per second.
    Cycles through the tick list endlessly.

    Args:
        ticker:         Stock symbol (e.g. "AAPL")
        ticks:          List of dicts with price and volume
        active_tickers: Shared dict updated in-place for WebSocket broadcast
    """
    client = get_redis_client()          # None if using in-memory
    create_timeseries_key(client, ticker)

    backend = "Redis" if _use_redis else "In-Memory"
    print(f"[DripFeed] RUNNING: {ticker} | {len(ticks)} ticks | backend: {backend}")

    idx = 0
    while True:
        if not ticks:
            await asyncio.sleep(config.DRIP_INTERVAL_SECONDS)
            continue

        tick_data = ticks[idx % len(ticks)]
        price = tick_data["price"]
        volume = tick_data["volume"]
        
        push_tick(client, ticker, price, volume)
        active_tickers[ticker] = price          # Live price for WebSocket

        idx += 1
        await asyncio.sleep(config.DRIP_INTERVAL_SECONDS)
