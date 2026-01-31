from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import requests

from agent_trading_company.core.paths import ensure_state_dir
from agent_trading_company.kis.errors import UnsupportedMarket

KIS_BASE_URL = "https://openapi.koreainvestment.com:9443"


class MissingEnvError(ValueError):
    pass


@dataclass(frozen=True)
class KISConfig:
    app_key: str
    app_secret: str
    cano: str
    acnt_prdt_cd: str
    base_url: str = KIS_BASE_URL
    id_type: str = "REAL"


def load_config_from_env() -> KISConfig:
    required = ["REAL_APP_KEY", "REAL_SECRET_KEY", "REAL_CANO", "REAL_ACNT_PRDT_CD"]
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise MissingEnvError(f"Missing env vars: {', '.join(missing)}")
    return KISConfig(
        app_key=os.environ["REAL_APP_KEY"],
        app_secret=os.environ["REAL_SECRET_KEY"],
        cano=os.environ["REAL_CANO"],
        acnt_prdt_cd=os.environ["REAL_ACNT_PRDT_CD"],
    )


def _default_sleep(seconds: float) -> None:
    time.sleep(seconds)


@dataclass
class KISClient:
    config: KISConfig
    token_path: Path
    session: requests.Session
    sleep_fn: Callable[[float], None] = _default_sleep

    @classmethod
    def from_env(cls, token_path: Path | None = None) -> "KISClient":
        config = load_config_from_env()
        state_dir = ensure_state_dir()
        token_path = token_path or (state_dir / "token_info.json")
        return cls(config=config, token_path=token_path, session=requests.Session())

    def _token_headers(self) -> dict[str, str]:
        token = self._get_access_token()
        return {
            "authorization": f"Bearer {token}",
            "appkey": self.config.app_key,
            "appsecret": self.config.app_secret,
            "custtype": "P",
        }

    def _token_payload(self) -> dict[str, str]:
        return {
            "grant_type": "client_credentials",
            "appkey": self.config.app_key,
            "appsecret": self.config.app_secret,
        }

    def _get_access_token(self) -> str:
        if self.token_path.exists():
            cached = json.loads(self.token_path.read_text(encoding="utf-8"))
            if cached.get("access_token") and cached.get("expired_at", 0) > time.time():
                return str(cached["access_token"])

        url = f"{self.config.base_url}/oauth2/tokenP"
        response = self.session.post(url, json=self._token_payload(), timeout=10)
        response.raise_for_status()
        data = response.json()
        token = data["access_token"]
        expires_in = int(data.get("expires_in", 0))
        payload = {
            "access_token": token,
            "expired_at": time.time() + max(expires_in - 60, 0),
        }
        self.token_path.parent.mkdir(parents=True, exist_ok=True)
        self.token_path.write_text(json.dumps(payload), encoding="utf-8")
        return token

    def _request(
        self,
        method: str,
        path: str,
        tr_id: str,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.config.base_url}{path}"
        headers = self._token_headers()
        headers["tr_id"] = tr_id
        attempt = 0
        while True:
            response = self.session.request(
                method,
                url,
                params=params,
                json=json_body,
                headers=headers,
                timeout=10,
            )
            if response.status_code not in (429, 500, 502, 503):
                response.raise_for_status()
                return response.json()
            if attempt >= 3:
                response.raise_for_status()
            delay = min(0.5 * (2**attempt), 4.0)
            self.sleep_fn(delay)
            attempt += 1

    def inquire_overseas_balance(self, excg_cd: str, crcy_cd: str) -> dict[str, Any]:
        params = {
            "CANO": self.config.cano,
            "ACNT_PRDT_CD": self.config.acnt_prdt_cd,
            "OVRS_EXCG_CD": excg_cd,
            "TR_CRCY_CD": crcy_cd,
            "CTX_AREA_FK200": "",
            "CTX_AREA_NK200": "",
        }
        return self._request(
            "GET",
            "/uapi/overseas-stock/v1/trading/inquire-balance",
            tr_id="TTTS3012R",
            params=params,
        )

    def inquire_overseas_price(self, excd: str, symb: str) -> dict[str, Any]:
        params = {"AUTH": "", "EXCD": excd, "SYMB": symb}
        return self._request(
            "GET",
            "/uapi/overseas-price/v1/quotations/price",
            tr_id="HHDFS00000300",
            params=params,
        )

    def inquire_overseas_price_detail(self, excd: str, symb: str) -> dict[str, Any]:
        params = {"AUTH": "", "EXCD": excd, "SYMB": symb}
        return self._request(
            "GET",
            "/uapi/overseas-price/v1/quotations/price-detail",
            tr_id="HHDFS76200200",
            params=params,
        )

    def place_overseas_order(
        self,
        side: str,
        excd: str,
        symb: str,
        qty: int,
        price: float | None,
    ) -> dict[str, Any]:
        tr_id = "TTTT1002U" if side.upper() == "BUY" else "TTTT1006U"
        payload = {
            "CANO": self.config.cano,
            "ACNT_PRDT_CD": self.config.acnt_prdt_cd,
            "OVRS_EXCG_CD": excd,
            "PDNO": symb,
            "ORD_QTY": str(qty),
            "OVRS_ORD_UNPR": "0" if price is None else str(price),
            "ORD_DVSN": "00",
        }
        return self._request(
            "POST",
            "/uapi/overseas-stock/v1/trading/order",
            tr_id=tr_id,
            json_body=payload,
        )

    def inquire_domestic_price(self, market_code: str, symbol: str) -> dict[str, Any]:
        params = {"FID_COND_MRKT_DIV_CODE": market_code, "FID_INPUT_ISCD": symbol}
        return self._request(
            "GET",
            "/uapi/domestic-stock/v1/quotations/inquire-price",
            tr_id="FHKST01010100",
            params=params,
        )

    def inquire_domestic_balance(self) -> dict[str, Any]:
        params = {
            "CANO": self.config.cano,
            "ACNT_PRDT_CD": self.config.acnt_prdt_cd,
            "AFHR_FLPR_YN": "N",
            "OFL_YN": "",
            "INQR_DVSN": "01",
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN": "00",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": "",
        }
        return self._request(
            "GET",
            "/uapi/domestic-stock/v1/trading/inquire-balance",
            tr_id="TTTC8434R",
            params=params,
        )

    def place_domestic_order(
        self,
        side: str,
        symbol: str,
        qty: int,
        price: float | None,
        market_code: str = "KRX",
    ) -> dict[str, Any]:
        tr_id = "TTTC0012U" if side.upper() == "BUY" else "TTTC0011U"
        payload = {
            "CANO": self.config.cano,
            "ACNT_PRDT_CD": self.config.acnt_prdt_cd,
            "PDNO": symbol,
            "ORD_DVSN": "00",
            "ORD_QTY": str(qty),
            "ORD_UNPR": "0" if price is None else str(price),
            "EXCG_ID_DVSN_CD": market_code,
            "SLL_TYPE": "",
            "CNDT_PRIC": "",
        }
        return self._request(
            "POST",
            "/uapi/domestic-stock/v1/trading/order-cash",
            tr_id=tr_id,
            json_body=payload,
        )

    def get_price(self, market_universe: str, exchange: str, symbol: str) -> dict[str, Any]:
        if market_universe.upper() == "KRX":
            return self.inquire_domestic_price(exchange, symbol)
        if market_universe.upper() == "OVERSEAS":
            return self.inquire_overseas_price(exchange, symbol)
        raise UnsupportedMarket(market_universe)

    def get_balance(self, market_universe: str, exchange: str, currency: str) -> dict[str, Any]:
        if market_universe.upper() == "KRX":
            return self.inquire_domestic_balance()
        if market_universe.upper() == "OVERSEAS":
            return self.inquire_overseas_balance(exchange, currency)
        raise UnsupportedMarket(market_universe)

    def place_order(
        self,
        market_universe: str,
        exchange: str,
        symbol: str,
        side: str,
        qty: int,
        price: float | None,
        currency: str = "USD",
    ) -> dict[str, Any]:
        if market_universe.upper() == "KRX":
            return self.place_domestic_order(side, symbol, qty, price, market_code=exchange)
        if market_universe.upper() == "OVERSEAS":
            return self.place_overseas_order(side, exchange, symbol, qty, price)
        raise UnsupportedMarket(market_universe)
