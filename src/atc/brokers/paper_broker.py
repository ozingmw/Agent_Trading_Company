from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from atc.types import AccountSnapshot, OrderRequest, OrderResult


@dataclass
class PaperOrder:
    order_id: str
    symbol: str
    side: str
    quantity: int
    status: str
    filled_price: Optional[float] = None


class PaperBroker:
    def __init__(self, starting_cash: float = 10_000_000.0) -> None:
        self.cash = starting_cash
        self.positions: Dict[str, int] = {}
        self.orders: List[PaperOrder] = []
        self.last_prices: Dict[str, float] = {}

    def update_prices(self, quotes: Dict[str, float]) -> None:
        self.last_prices.update(quotes)

    def get_account(self) -> AccountSnapshot:
        return AccountSnapshot(cash=self.cash, positions=dict(self.positions))

    def get_positions(self) -> Dict[str, int]:
        return dict(self.positions)

    def get_orders(self) -> List[PaperOrder]:
        return list(self.orders)

    def place_order(self, request: OrderRequest) -> OrderResult:
        order_id = str(uuid.uuid4())
        price = request.limit_price or self.last_prices.get(request.symbol)
        if price is None:
            return OrderResult(
                symbol=request.symbol,
                market=request.market,
                side=request.side,
                quantity=request.quantity,
                status="REJECTED_NO_PRICE",
            )

        cost = price * request.quantity
        if request.side == "BUY" and cost > self.cash:
            return OrderResult(
                symbol=request.symbol,
                market=request.market,
                side=request.side,
                quantity=request.quantity,
                status="REJECTED_NO_CASH",
            )

        if request.side == "SELL":
            held = self.positions.get(request.symbol, 0)
            if held < request.quantity:
                return OrderResult(
                    symbol=request.symbol,
                    market=request.market,
                    side=request.side,
                    quantity=request.quantity,
                    status="REJECTED_NO_SHARES",
                )

        if request.side == "BUY":
            self.cash -= cost
            self.positions[request.symbol] = self.positions.get(request.symbol, 0) + request.quantity
        else:
            self.cash += cost
            self.positions[request.symbol] = self.positions.get(request.symbol, 0) - request.quantity

        order = PaperOrder(
            order_id=order_id,
            symbol=request.symbol,
            side=request.side,
            quantity=request.quantity,
            status="FILLED",
            filled_price=price,
        )
        self.orders.append(order)
        return OrderResult(
            symbol=request.symbol,
            market=request.market,
            side=request.side,
            quantity=request.quantity,
            status="FILLED",
            broker_order_id=order_id,
            filled_price=price,
        )
