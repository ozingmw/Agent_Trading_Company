from __future__ import annotations

from typing import Protocol


class Store(Protocol):
    def save_order(self, order: dict[str, object]) -> None:
        ...

    def get_orders(self, filters: dict[str, object] | None = None) -> list[dict[str, object]]:
        ...

    def save_position(self, position: dict[str, object]) -> None:
        ...

    def get_positions(self) -> list[dict[str, object]]:
        ...

    def save_pnl(self, pnl: dict[str, object]) -> None:
        ...

    def get_pnl_window(self, n: int) -> list[dict[str, object]]:
        ...

    def register_data(self, source: str, path: str, metadata: dict[str, object]) -> None:
        ...

    def get_latest_data(self, source: str) -> dict[str, object] | None:
        ...
