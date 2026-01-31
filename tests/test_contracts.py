import pytest

from agent_trading_company.core.contracts import Role, Status, validate_artifact


def sample_artifact(payload: dict[str, object]) -> dict[str, object]:
    return {
        "artifact_id": "a1",
        "agent_id": "analyst-1",
        "role": Role.ANALYST.value,
        "created_at": "2026-01-29T12:01:00Z",
        "inputs": [],
        "outputs": ["artifacts/analyst/sample.md"],
        "directive_hash": "deadbeef",
        "payload": payload,
        "status": Status.COMPLETED,
    }


def test_contract_requires_fields():
    data = sample_artifact(
        {
            "symbol": "005930.KS",
            "exchange": "KRX",
            "side": "BUY",
            "order_type": "LIMIT",
            "limit_price": 70000,
            "size_hint": 100,
            "confidence": 0.62,
        }
    )
    data.pop("artifact_id")
    with pytest.raises(Exception):
        _ = validate_artifact(data)


def test_analyst_payload_requires_symbol():
    payload = {
        "exchange": "KRX",
        "side": "BUY",
        "order_type": "LIMIT",
        "limit_price": 70000,
        "size_hint": 100,
        "confidence": 0.62,
    }
    with pytest.raises(Exception):
        _ = validate_artifact(sample_artifact(payload))
