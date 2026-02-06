from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Set


@dataclass
class UniverseSnapshot:
    symbols_kr: List[str]
    symbols_us: List[str]
    trends: List[str]


class UniverseManager:
    def __init__(self, seed_kr: List[str], seed_us: List[str], max_symbols: int) -> None:
        self._symbols_kr: Set[str] = set(seed_kr)
        self._symbols_us: Set[str] = set(seed_us)
        self._max = max_symbols
        self._trends: List[str] = []

    def snapshot(self) -> UniverseSnapshot:
        return UniverseSnapshot(
            symbols_kr=sorted(self._symbols_kr),
            symbols_us=sorted(self._symbols_us),
            trends=list(self._trends),
        )

    def update_trends(self, trends: List[str]) -> None:
        self._trends = trends[:20]

    def add_symbols(self, symbols_kr: List[str], symbols_us: List[str]) -> None:
        for symbol in symbols_kr:
            if len(self._symbols_kr) >= self._max:
                break
            self._symbols_kr.add(symbol)
        for symbol in symbols_us:
            if len(self._symbols_us) >= self._max:
                break
            self._symbols_us.add(symbol)
