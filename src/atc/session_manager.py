from __future__ import annotations

from datetime import datetime
from typing import Optional

from atc.config import MarketsConfig
from atc.utils.time import is_market_open_kr, is_market_open_us


class SessionManager:
    def __init__(self, markets: MarketsConfig) -> None:
        self.markets = markets

    def is_open(self, market: str, now: Optional[datetime] = None) -> bool:
        if market == "KR" and self.markets.enable_kr:
            return is_market_open_kr(now)
        if market == "US" and self.markets.enable_us:
            return is_market_open_us(now)
        return False

    def any_open(self, now: Optional[datetime] = None) -> bool:
        return self.is_open("KR", now) or self.is_open("US", now)
