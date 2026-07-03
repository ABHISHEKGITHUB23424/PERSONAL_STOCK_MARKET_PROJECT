# =============================================================================
# velocity.py — The 'Pace' Calculator
#
# Calculates price velocity (change per hour) from the last 60 ticks.
# Works with both Redis and in-memory fallback transparently.
#
# Formula:
#   velocity = (last_price - first_price) / elapsed_hours
#   60 ticks × 1 sec/tick = 60 seconds = 0.01667 hours
# =============================================================================

from typing import Optional
import config
from redis_writer import get_redis_client, get_last_n_ticks
from typing import Optional, Tuple


def calculate_velocity(ticker: str) -> Optional[float]:
    """
    Calculate price velocity (price change per hour) using last N ticks.

    Returns:
        float  — positive = rising, negative = falling
        None   — not enough ticks yet
    """
    client = get_redis_client()          # None if using in-memory backend
    ticks  = get_last_n_ticks(client, ticker, config.VELOCITY_WINDOW)

    if len(ticks) < 2:
        return None

    first_price = ticks[0]["price"]
    last_price  = ticks[-1]["price"]

    elapsed_seconds = len(ticks) * config.DRIP_INTERVAL_SECONDS
    elapsed_hours   = elapsed_seconds / 3600.0

    if elapsed_hours == 0:
        return 0.0

    velocity = (last_price - first_price) / elapsed_hours
    return round(velocity, 4)


def calculate_vwap(ticker: str) -> Optional[float]:
    """
    Calculates Volume Weighted Average Price (VWAP) over the VELOCITY_WINDOW.
    VWAP = sum(Price * Volume) / sum(Volume)
    """
    client = get_redis_client()
    ticks  = get_last_n_ticks(client, ticker, config.VELOCITY_WINDOW)

    if not ticks:
        return None

    total_value = 0.0
    total_volume = 0.0

    for tick in ticks:
        p = tick["price"]
        v = tick["volume"]
        total_value += p * v
        total_volume += v

    if total_volume == 0:
        return ticks[-1]["price"]

    return round(total_value / total_volume, 4)


def calculate_relative_volume(ticker: str) -> Optional[float]:
    """
    Calculates the Relative Volume (RVOL) based on recent ticks vs typical volume.
    Mock calculation: compares last 10 ticks volume against the full VELOCITY_WINDOW average.
    """
    client = get_redis_client()
    ticks  = get_last_n_ticks(client, ticker, config.VELOCITY_WINDOW)

    if len(ticks) < 20:
        return None

    recent_ticks = ticks[-10:]
    avg_recent_vol = sum(t["volume"] for t in recent_ticks) / 10.0
    avg_total_vol = sum(t["volume"] for t in ticks) / len(ticks)

    if avg_total_vol == 0:
        return 1.0

    return round(avg_recent_vol / avg_total_vol, 2)

