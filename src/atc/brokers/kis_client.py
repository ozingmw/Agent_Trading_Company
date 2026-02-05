from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, List, Optional

import requests

from atc.config import AppConfig, Secrets
from atc.types import AccountSnapshot, OrderRequest, OrderResult


@dataclass
class KisToken:
    value: str
    expires_at: float


class KisClient:
    def __init__(self, config: AppConfig, secrets: Secrets) -> None:
        self.config = config
        self.secrets = secrets
        self.base_url = config.kis.base_url.rstrip("/")
        self.token_url = (
            config.kis.token_url_paper if config.kis.mode == "paper" else config.kis.token_url_live
        )
        self._token: Optional[KisToken] = None
        self.enabled = all(
            [secrets.kis_app_key, secrets.kis_app_secret, secrets.kis_account_no]
        )

    def _get_token(self) -> Optional[str]:
        if not self.enabled:
            return None
        now = time.time()
        if self._token and self._token.expires_at > now + 60:
            return self._token.value
        payload = {
            "grant_type": "client_credentials",
            "appkey": self.secrets.kis_app_key,
            "appsecret": self.secrets.kis_app_secret,
        }
        resp = requests.post(self.token_url, json=payload, timeout=10)
        if resp.status_code != 200:
            return None
        data = resp.json()
        access_token = data.get("access_token")
        expires_in = int(data.get("expires_in", 0))
        if not access_token:
            return None
        self._token = KisToken(value=access_token, expires_at=now + expires_in)
        return access_token

    def _headers(self, tr_id: str) -> Dict[str, str]:
        token = self._get_token()
        headers = {
            "appkey": self.secrets.kis_app_key or "",
            "appsecret": self.secrets.kis_app_secret or "",
            "tr_id": tr_id,
        }
        if token:
            headers["authorization"] = f"Bearer {token}"
        return headers

    def get_quotes(self, symbols: List[str], market: str) -> Dict[str, float]:
        if not self.enabled:
            return {}
        quotes: Dict[str, float] = {}
        for symbol in symbols:
            if market == "KR":
                endpoint = "uapi/domestic-stock/v1/quotations/inquire-price"
                params = {"fid_cond_mrkt_div_code": "J", "fid_input_iscd": symbol}
                tr_id = "FHKST01010100"
            else:
                endpoint = "uapi/overseas-stock/v1/quotations/price"
                params = {"EXCD": "NAS", "SYMB": symbol}
                tr_id = "HHDFS00000300"
            url = f"{self.base_url}/{endpoint}"
            resp = requests.get(url, headers=self._headers(tr_id), params=params, timeout=10)
            if resp.status_code != 200:
                continue
            data = resp.json()
            if market == "KR":
                price = data.get("output", {}).get("stck_prpr")
            else:
                price = data.get("output", {}).get("last")
            try:
                quotes[symbol] = float(price)
            except (TypeError, ValueError):
                continue
        return quotes

    def get_positions(self) -> Dict[str, int]:
        if not self.enabled:
            return {}
        endpoint = "uapi/domestic-stock/v1/trading/inquire-balance"
        tr_id = "TTTC8434R"
        params = {
            "CANO": self.secrets.kis_account_no or "",
            "ACNT_PRDT_CD": "01",
            "AFHR_FLPR_YN": "N",
            "OFL_YN": "N",
            "INQR_DVSN": "02",
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN": "00",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": "",
        }
        url = f"{self.base_url}/{endpoint}"
        resp = requests.get(url, headers=self._headers(tr_id), params=params, timeout=10)
        if resp.status_code != 200:
            return {}
        data = resp.json()
        positions: Dict[str, int] = {}
        for item in data.get("output1", []) or []:
            symbol = item.get("pdno")
            qty = item.get("hldg_qty")
            if symbol and qty:
                try:
                    positions[symbol] = int(float(qty))
                except ValueError:
                    continue
        return positions

    def get_orders(self) -> List[Dict[str, str]]:
        if not self.enabled:
            return []
        return []

    def get_account(self) -> AccountSnapshot:
        if not self.enabled:
            return AccountSnapshot(cash=0.0, positions={})
        endpoint = "uapi/domestic-stock/v1/trading/inquire-balance"
        tr_id = "TTTC8434R"
        params = {
            "CANO": self.secrets.kis_account_no or "",
            "ACNT_PRDT_CD": "01",
            "AFHR_FLPR_YN": "N",
            "OFL_YN": "N",
            "INQR_DVSN": "02",
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN": "00",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": "",
        }
        url = f"{self.base_url}/{endpoint}"
        resp = requests.get(url, headers=self._headers(tr_id), params=params, timeout=10)
        if resp.status_code != 200:
            return AccountSnapshot(cash=0.0, positions={})
        data = resp.json()
        cash = 0.0
        try:
            cash = float(data.get("output2", [{}])[0].get("dnca_tot_amt", 0))
        except (TypeError, ValueError):
            cash = 0.0
        return AccountSnapshot(cash=cash, positions=self.get_positions())

    def place_order(self, request: OrderRequest) -> OrderResult:
        if not self.enabled:
            return OrderResult(
                symbol=request.symbol,
                market=request.market,
                side=request.side,
                quantity=request.quantity,
                status="REJECTED_NO_CREDENTIALS",
            )
        endpoint = "uapi/domestic-stock/v1/trading/order-cash"
        tr_id = "TTTC0802U" if request.side == "BUY" else "TTTC0801U"
        payload = {
            "CANO": self.secrets.kis_account_no or "",
            "ACNT_PRDT_CD": "01",
            "PDNO": request.symbol,
            "ORD_DVSN": "00" if request.order_type == "MARKET" else "01",
            "ORD_QTY": str(request.quantity),
            "ORD_UNPR": "0" if request.order_type == "MARKET" else str(request.limit_price or 0),
        }
        url = f"{self.base_url}/{endpoint}"
        resp = requests.post(url, headers=self._headers(tr_id), json=payload, timeout=10)
        if resp.status_code != 200:
            return OrderResult(
                symbol=request.symbol,
                market=request.market,
                side=request.side,
                quantity=request.quantity,
                status=f"REJECTED_{resp.status_code}",
            )
        data = resp.json()
        order_id = data.get("output", {}).get("ODNO")
        return OrderResult(
            symbol=request.symbol,
            market=request.market,
            side=request.side,
            quantity=request.quantity,
            status="SUBMITTED",
            broker_order_id=order_id,
        )
