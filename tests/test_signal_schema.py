import pytest

from atc.types import SignalIntent


def test_signal_intent_valid() -> None:
    intent = SignalIntent(
        symbol="AAPL",
        market="US",
        action="BUY",
        confidence=0.7,
        horizon="intraday",
        order_type="MARKET",
        size=10,
        rationale="momentum",
        data_used=["quotes", "news"],
    )
    assert intent.symbol == "AAPL"


def test_signal_intent_invalid_action() -> None:
    with pytest.raises(Exception):
        SignalIntent(
            symbol="AAPL",
            market="US",
            action="LONG",
            confidence=0.7,
            horizon="intraday",
            order_type="MARKET",
            size=10,
            rationale="momentum",
            data_used=["quotes"],
        )
