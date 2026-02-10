"""
Async HTTP client for the KIS (Korea Investment & Securities) Open API.

Uses httpx.AsyncClient for non-blocking I/O and caches the OAuth2 token
until expiry so that callers never need to manage authentication manually.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import httpx

from kis.endpoints import ENDPOINTS, get_tr_id
from kis.models import (
    AccountBalance,
    BalanceItem,
    DailyPrice,
    OrderOutput,
    OrderResponse,
    StockPrice,
    TokenResponse,
)

if TYPE_CHECKING:
    from config import Config

logger = logging.getLogger(__name__)


class KISClient:
    """Async client wrapping KIS Open API endpoints.

    Args:
        config: Application Config instance containing KIS credentials
                and trading-mode settings.
    """

    # KIS API rate limit: minimum seconds between requests
    # Paper trading server is stricter — 0.25s avoids 500 errors
    _REQUEST_INTERVAL = 0.25
    # Retry settings for transient server errors (5xx)
    _MAX_RETRIES = 3
    _RETRY_BACKOFF = 0.5  # seconds; doubles each retry

    def __init__(self, config: Config) -> None:
        self.config = config
        self.client = httpx.AsyncClient(
            base_url=config.kis_base_url,
            timeout=30.0,
        )
        self._token: str | None = None
        self._token_expires: datetime | None = None
        self._token_lock = asyncio.Lock()
        self._rate_lock = asyncio.Lock()
        self._last_request_time: float = 0.0

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    async def get_token(self) -> str:
        """Obtain (or return cached) OAuth2 access token.

        Uses an asyncio.Lock to prevent concurrent token requests when
        multiple agents start simultaneously.

        Returns:
            Bearer access-token string.
        """
        if self._token and self._token_expires and datetime.now() < self._token_expires:
            return self._token

        async with self._token_lock:
            # Double-check after acquiring lock (another coroutine may have refreshed)
            if self._token and self._token_expires and datetime.now() < self._token_expires:
                return self._token

            body = {
                "grant_type": "client_credentials",
                "appkey": self.config.kis_app_key,
                "appsecret": self.config.kis_app_secret,
            }

            resp = await self.client.post(ENDPOINTS["token"], json=body)
            resp.raise_for_status()
            token_data = TokenResponse(**resp.json())

            self._token = token_data.access_token
            self._token_expires = datetime.now() + timedelta(
                seconds=token_data.expires_in - 60
            )

            logger.info("KIS access token acquired (expires in %ds)", token_data.expires_in)
            return self._token

    async def _ensure_token(self) -> None:
        """Ensure a valid token is cached, refreshing if necessary."""
        await self.get_token()

    # ------------------------------------------------------------------
    # Rate-limited request helpers
    # ------------------------------------------------------------------

    async def _throttle(self) -> None:
        """Ensure minimum interval between API requests."""
        async with self._rate_lock:
            now = time.monotonic()
            elapsed = now - self._last_request_time
            if elapsed < self._REQUEST_INTERVAL:
                await asyncio.sleep(self._REQUEST_INTERVAL - elapsed)
            self._last_request_time = time.monotonic()

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        **kwargs: object,
    ) -> httpx.Response:
        """Execute an HTTP request with rate-limiting and retry on 5xx errors."""
        last_exc: Exception | None = None
        for attempt in range(self._MAX_RETRIES):
            await self._throttle()
            resp = await self.client.request(method, url, **kwargs)
            if resp.status_code < 500:
                return resp
            last_exc = httpx.HTTPStatusError(
                f"Server error '{resp.status_code}'",
                request=resp.request,
                response=resp,
            )
            wait = self._RETRY_BACKOFF * (2 ** attempt)
            logger.warning(
                "KIS API %s %s returned %d, retrying in %.1fs (attempt %d/%d)",
                method, url, resp.status_code, wait, attempt + 1, self._MAX_RETRIES,
            )
            await asyncio.sleep(wait)
        # All retries exhausted — raise the last error
        raise last_exc  # type: ignore[misc]

    # ------------------------------------------------------------------
    # Headers & hashkey
    # ------------------------------------------------------------------

    async def _get_headers(self, tr_id: str) -> dict[str, str]:
        """Build the standard header dict required by most KIS endpoints.

        Args:
            tr_id: KIS transaction ID for the target endpoint.

        Returns:
            Header dictionary with authorization, appkey, appsecret, tr_id,
            and custtype fields.
        """
        await self._ensure_token()
        return {
            "Content-Type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self._token}",
            "appkey": self.config.kis_app_key,
            "appsecret": self.config.kis_app_secret,
            "tr_id": tr_id,
            "custtype": "P",
        }

    async def _get_hashkey(self, data: dict) -> str:
        """Generate a hashkey for order request bodies.

        The KIS API requires a ``hashkey`` header on POST trading requests.
        This method calls the ``/uapi/hashkey`` endpoint to compute it.

        Args:
            data: The JSON body that will be sent in the trading request.

        Returns:
            hashkey string.
        """
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "appkey": self.config.kis_app_key,
            "appsecret": self.config.kis_app_secret,
        }
        resp = await self._request_with_retry("POST", ENDPOINTS["hashkey"], json=data, headers=headers)
        resp.raise_for_status()
        return resp.json()["HASH"]

    # ------------------------------------------------------------------
    # Market data
    # ------------------------------------------------------------------

    async def get_price(self, stock_code: str) -> StockPrice:
        """Fetch the current quote for a single stock.

        Args:
            stock_code: 6-digit KRX stock code (e.g. ``"005930"``).

        Returns:
            Parsed :class:`StockPrice` model.
        """
        tr_id = get_tr_id("price", self.config.trading_mode)
        headers = await self._get_headers(tr_id)
        params = {
            "fid_cond_mrkt_div_code": "J",
            "fid_input_iscd": stock_code,
        }

        resp = await self._request_with_retry("GET", ENDPOINTS["price"], headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()

        if data.get("rt_cd") != "0":
            raise RuntimeError(
                f"KIS price API error: [{data.get('msg_cd')}] {data.get('msg1')}"
            )

        return StockPrice(**data["output"])

    async def get_daily_prices(
        self,
        stock_code: str,
        period: str = "D",
        count: int = 30,
    ) -> list[DailyPrice]:
        """Fetch daily OHLCV history for a stock.

        Args:
            stock_code: 6-digit KRX stock code.
            period: Period type — ``"D"`` (day), ``"W"`` (week), ``"M"`` (month).
            count: Maximum number of records to return (KIS may cap this).

        Returns:
            List of :class:`DailyPrice` entries, most recent first.
        """
        tr_id = get_tr_id("daily_price", self.config.trading_mode)
        headers = await self._get_headers(tr_id)
        params = {
            "fid_cond_mrkt_div_code": "J",
            "fid_input_iscd": stock_code,
            "fid_input_date_1": "",
            "fid_input_date_2": "",
            "fid_period_div_code": period,
            "fid_org_adj_prc": "0",
        }

        resp = await self._request_with_retry(
            "GET", ENDPOINTS["daily_price"], headers=headers, params=params
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("rt_cd") != "0":
            raise RuntimeError(
                f"KIS daily-price API error: [{data.get('msg_cd')}] {data.get('msg1')}"
            )

        items = data.get("output2", [])
        return [DailyPrice(**item) for item in items[:count]]

    # ------------------------------------------------------------------
    # Trading
    # ------------------------------------------------------------------

    async def _place_order(
        self,
        side: str,
        stock_code: str,
        qty: int,
        price: int = 0,
        order_type: str = "01",
    ) -> OrderResponse:
        """Internal helper to place a buy or sell order.

        Args:
            side: ``"buy"`` or ``"sell"``.
            stock_code: 6-digit KRX stock code.
            qty: Order quantity.
            price: Order unit price (0 for market order when order_type allows).
            order_type: KIS order division code (``"01"`` = limit, ``"00"`` = market, etc.).

        Returns:
            Parsed :class:`OrderResponse`.
        """
        tr_id = get_tr_id(side, self.config.trading_mode)
        body = {
            "CANO": self.config.kis_account_no,
            "ACNT_PRDT_CD": self.config.kis_acnt_prdt_cd,
            "PDNO": stock_code,
            "ORD_DVSN": order_type,
            "ORD_QTY": str(qty),
            "ORD_UNPR": str(price),
        }

        hashkey = await self._get_hashkey(body)
        headers = await self._get_headers(tr_id)
        headers["hashkey"] = hashkey

        resp = await self._request_with_retry("POST", ENDPOINTS["order"], json=body, headers=headers)
        resp.raise_for_status()
        data = resp.json()

        output = OrderOutput(**data["output"]) if data.get("output") else None
        return OrderResponse(
            rt_cd=data.get("rt_cd", ""),
            msg_cd=data.get("msg_cd", ""),
            msg1=data.get("msg1", ""),
            output=output,
        )

    async def buy(
        self,
        stock_code: str,
        qty: int,
        price: int = 0,
        order_type: str = "01",
    ) -> OrderResponse:
        """Place a buy (cash) order.

        Args:
            stock_code: 6-digit KRX stock code.
            qty: Number of shares to buy.
            price: Limit price per share. Use ``0`` with ``order_type="00"``
                   for a market order.
            order_type: ``"01"`` (limit) or ``"00"`` (market), among others.

        Returns:
            Parsed :class:`OrderResponse` with order number on success.
        """
        logger.info(
            "BUY  %s  qty=%d  price=%d  type=%s", stock_code, qty, price, order_type
        )
        return await self._place_order("buy", stock_code, qty, price, order_type)

    async def sell(
        self,
        stock_code: str,
        qty: int,
        price: int = 0,
        order_type: str = "01",
    ) -> OrderResponse:
        """Place a sell (cash) order.

        Args:
            stock_code: 6-digit KRX stock code.
            qty: Number of shares to sell.
            price: Limit price per share.
            order_type: ``"01"`` (limit) or ``"00"`` (market), among others.

        Returns:
            Parsed :class:`OrderResponse` with order number on success.
        """
        logger.info(
            "SELL %s  qty=%d  price=%d  type=%s", stock_code, qty, price, order_type
        )
        return await self._place_order("sell", stock_code, qty, price, order_type)

    # ------------------------------------------------------------------
    # Account
    # ------------------------------------------------------------------

    async def get_balance(self) -> AccountBalance:
        """Fetch current account balance and holdings.

        Returns:
            Parsed :class:`AccountBalance` containing individual
            :class:`BalanceItem` entries and totals.
        """
        tr_id = get_tr_id("balance", self.config.trading_mode)
        headers = await self._get_headers(tr_id)
        params = {
            "CANO": self.config.kis_account_no,
            "ACNT_PRDT_CD": self.config.kis_acnt_prdt_cd,
            "AFHR_FLPR_YN": "N",
            "OFL_YN": "",
            "INQR_DVSN": "01",
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN": "01",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": "",
        }

        resp = await self._request_with_retry(
            "GET", ENDPOINTS["balance"], headers=headers, params=params
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("rt_cd") != "0":
            raise RuntimeError(
                f"KIS balance API error: [{data.get('msg_cd')}] {data.get('msg1')}"
            )

        items = [BalanceItem(**item) for item in data.get("output1", [])]

        totals = data.get("output2", [{}])
        total_block = totals[0] if isinstance(totals, list) and totals else totals

        return AccountBalance(
            items=items,
            total_evlu_amt=total_block.get("tot_evlu_amt", "0"),
            total_evlu_pfls_amt=total_block.get("evlu_pfls_smtl_amt", "0"),
        )

    async def get_available_cash(self) -> int:
        """Fetch available cash from the balance endpoint.

        Uses ``inquire-balance`` output2 ``dnca_tot_amt`` (total deposit)
        instead of ``inquire-psbl-order`` which requires a specific stock code.

        Returns:
            Available cash as an integer (KRW).
        """
        tr_id = get_tr_id("balance", self.config.trading_mode)
        headers = await self._get_headers(tr_id)
        params = {
            "CANO": self.config.kis_account_no,
            "ACNT_PRDT_CD": self.config.kis_acnt_prdt_cd,
            "AFHR_FLPR_YN": "N",
            "OFL_YN": "",
            "INQR_DVSN": "01",
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN": "01",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": "",
        }

        resp = await self._request_with_retry(
            "GET", ENDPOINTS["balance"], headers=headers, params=params
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("rt_cd") != "0":
            raise RuntimeError(
                f"KIS available-cash API error: [{data.get('msg_cd')}] {data.get('msg1')}"
            )

        totals = data.get("output2", [{}])
        total_block = totals[0] if isinstance(totals, list) and totals else totals
        return int(total_block.get("dnca_tot_amt", "0"))

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def close(self) -> None:
        """Close the underlying httpx client and release resources."""
        await self.client.aclose()
        logger.info("KIS client closed")

    async def __aenter__(self) -> KISClient:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.close()
