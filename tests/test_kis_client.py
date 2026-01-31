from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
import responses
import requests

from agent_trading_company.kis.client import KISClient, KISConfig, MissingEnvError


def test_missing_env_vars_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("REAL_APP_KEY", raising=False)
    monkeypatch.delenv("REAL_SECRET_KEY", raising=False)
    monkeypatch.delenv("REAL_CANO", raising=False)
    monkeypatch.delenv("REAL_ACNT_PRDT_CD", raising=False)

    with pytest.raises(MissingEnvError):
        _ = KISClient.from_env()


@responses.activate
def test_token_cache_read_write(tmp_path: Path) -> None:
    token_path = tmp_path / "state" / "token_info.json"
    token_path.parent.mkdir(parents=True, exist_ok=True)

    cached = {"access_token": "cached", "expired_at": 9999999999}
    token_path.write_text(json.dumps(cached), encoding="utf-8")

    config = KISConfig("key", "secret", "123", "01")
    client = KISClient(config=config, token_path=token_path, session=requests.Session())
    assert client._get_access_token() == "cached"

    token_path.unlink()
    responses.add(
        responses.POST,
        f"{config.base_url}/oauth2/tokenP",
        json={"access_token": "fresh", "expires_in": 3600},
        status=200,
    )
    assert client._get_access_token() == "fresh"
    stored = json.loads(token_path.read_text(encoding="utf-8"))
    assert stored["access_token"] == "fresh"


@responses.activate
def test_overseas_price_request_headers(tmp_path: Path) -> None:
    token_path = tmp_path / "state" / "token_info.json"
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(
        json.dumps({"access_token": "cached", "expired_at": 9999999999}),
        encoding="utf-8",
    )

    config = KISConfig("key", "secret", "123", "01")
    client = KISClient(config=config, token_path=token_path, session=requests.Session())

    responses.add(
        responses.GET,
        f"{config.base_url}/uapi/overseas-price/v1/quotations/price",
        json={"output": {"price": "123"}},
        status=200,
    )

    _ = client.inquire_overseas_price("NASD", "AAPL")

    request = responses.calls[0].request
    assert request.headers["authorization"] == "Bearer cached"
    assert request.headers["appkey"] == "key"
    assert request.headers["appsecret"] == "secret"
    assert request.headers["tr_id"] == "HHDFS00000300"
