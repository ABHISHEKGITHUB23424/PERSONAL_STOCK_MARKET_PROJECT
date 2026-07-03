# =============================================================================
# feed/base_feed.py — Abstract base class for ALL data feeds
#
# ⚡ SWAP POINT: To use a real broker (KiteTicker, Alpaca, etc.),
#    create a new file in this folder (e.g. kite_feed.py) that inherits
#    from AbstractFeed and implement get_ticks(). Then change FEED_MODULE
#    in config.py. NOTHING else changes in the rest of the system.
# =============================================================================

from abc import ABC, abstractmethod
from typing import List


class AbstractFeed(ABC):
    """
    All data feeds MUST implement this interface.
    The rest of the system only talks to AbstractFeed — never to a
    concrete implementation — making the feed 100% swappable.
    """

    @abstractmethod
    def get_ticks(self, ticker: str) -> List[dict]:
        """
        Fetch a list of price and volume ticks for the given ticker.

        Returns:
            A list of dicts like {"price": 150.0, "volume": 1200}, ordered oldest → newest.
            Each dict represents one simulated 'tick'.
        """
        ...

    @abstractmethod
    def get_feed_name(self) -> str:
        """Return a human-readable name for this feed (used in logs)."""
        ...
