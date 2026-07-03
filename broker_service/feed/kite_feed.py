# =============================================================================
# feed/kite_feed.py — PLACEHOLDER for real KiteTicker integration
#
# When you're ready to go live with Zerodha Kite:
#   1. Fill in the KiteTicker logic below
#   2. Change FEED_MODULE = "kite" in config.py
#   That's it. Nothing else changes.
# =============================================================================

from typing import List
from .base_feed import AbstractFeed


class KiteFeed(AbstractFeed):
    """
    PLACEHOLDER — Real broker feed via Zerodha KiteTicker WebSocket.
    Implement this when going live.
    """

    def get_feed_name(self) -> str:
        return "KiteTicker (Zerodha — LIVE)"

    def get_ticks(self, ticker: str) -> List[float]:
        """
        TODO: Connect to KiteTicker WebSocket and stream live prices.

        Example KiteTicker usage:
            from kiteconnect import KiteTicker
            kt = KiteTicker(api_key, access_token)
            kt.on_ticks = on_ticks_callback
            kt.connect()
        """
        raise NotImplementedError(
            "KiteFeed is a placeholder. "
            "Implement KiteTicker WebSocket logic here."
        )
