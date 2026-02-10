"""
KIS WebSocket client for real-time stock price streaming.

Connects to KIS WebSocket API, subscribes to real-time execution prices
(H0STCNT0) for given stock codes, and invokes a callback on each tick.

Protocol reference (KIS Open API):
  1. Obtain approval_key via POST /oauth2/Approval
  2. Connect to ws://ops.koreainvestment.com:31000 (paper) or :21000 (live)
  3. Send JSON subscribe messages with tr_id=H0STCNT0
  4. Receive pipe-delimited messages: "0|H0STCNT0|count|field0^field1^..."
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Callable, Awaitable

import httpx
import websockets
from websockets.asyncio.client import connect as ws_connect

from kis.endpoints import ENDPOINTS

logger = logging.getLogger(__name__)

# Real-time execution price field indices (주식체결 H0STCNT0)
# The ^-delimited payload has these fields (0-indexed):
F_STOCK_CODE = 0   # MKSC_SHRN_ISCD
F_TIME = 1         # STCK_CNTG_HOUR (HHMMSS)
F_PRICE = 2        # STCK_PRPR (current price)
F_SIGN = 3         # PRDY_VRSS_SIGN (1=up-limit,2=up,3=flat,4=down,5=down-limit)
F_CHANGE = 4       # PRDY_VRSS (change amount)
F_CHANGE_RATE = 5  # PRDY_CTRT (change rate %)
F_OPEN = 7         # STCK_OPRC
F_HIGH = 8         # STCK_HGPR
F_LOW = 9          # STCK_LWPR
F_VOLUME = 13      # ACML_VOL (accumulated volume)

# Type alias for the callback
PriceCallback = Callable[[dict[str, str]], Awaitable[None]]


class KISWebSocket:
    """Async KIS WebSocket client for real-time price streaming."""

    TR_ID = "H0STCNT0"  # 주식체결 (real-time execution price)

    def __init__(
        self,
        config: Any,
        on_price: PriceCallback | None = None,
    ) -> None:
        self.config = config
        self.on_price = on_price
        self._approval_key: str | None = None
        self._ws: Any = None
        self._subscribed: set[str] = set()

    # ------------------------------------------------------------------
    # Approval key (WebSocket authentication)
    # ------------------------------------------------------------------

    async def _get_approval_key(self) -> str:
        """Obtain WebSocket approval key from KIS REST API."""
        if self._approval_key:
            return self._approval_key

        async with httpx.AsyncClient(base_url=self.config.kis_base_url, timeout=10.0) as client:
            resp = await client.post(
                ENDPOINTS["approval"],
                json={
                    "grant_type": "client_credentials",
                    "appkey": self.config.kis_app_key,
                    "secretkey": self.config.kis_app_secret,
                },
            )
            resp.raise_for_status()
            self._approval_key = resp.json()["approval_key"]
            logger.info("KIS WebSocket approval key acquired")
            return self._approval_key

    # ------------------------------------------------------------------
    # Subscribe / unsubscribe
    # ------------------------------------------------------------------

    def _build_subscribe_msg(self, stock_code: str, subscribe: bool = True) -> str:
        """Build a JSON subscribe/unsubscribe message."""
        return json.dumps({
            "header": {
                "approval_key": self._approval_key,
                "custtype": "P",
                "tr_type": "1" if subscribe else "2",
                "content-type": "utf-8",
            },
            "body": {
                "input": {
                    "tr_id": self.TR_ID,
                    "tr_key": stock_code,
                },
            },
        })

    async def subscribe(self, stock_codes: list[str]) -> None:
        """Subscribe to real-time prices for given stock codes."""
        if not self._ws:
            return
        for code in stock_codes:
            if code in self._subscribed:
                continue
            await self._ws.send(self._build_subscribe_msg(code, subscribe=True))
            self._subscribed.add(code)
            logger.info("Subscribed to real-time price: %s", code)
            await asyncio.sleep(0.1)  # small delay between subscriptions

    # ------------------------------------------------------------------
    # Message parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_price_message(raw: str) -> dict[str, str] | None:
        """Parse a pipe-delimited price message into a dict.

        Format: "encrypted|tr_id|count|data"
        Data is ^-delimited fields.
        Returns None if not a price data message.
        """
        parts = raw.split("|")
        if len(parts) < 4:
            return None

        encrypted = parts[0]
        tr_id = parts[1]

        # Only handle unencrypted price messages
        if encrypted != "0" or tr_id != "H0STCNT0":
            return None

        fields = parts[3].split("^")
        if len(fields) <= F_VOLUME:
            return None

        return {
            "stock_code": fields[F_STOCK_CODE],
            "price": fields[F_PRICE],
            "change_sign": fields[F_SIGN],
            "change_amount": fields[F_CHANGE],
            "change_rate": fields[F_CHANGE_RATE],
            "open": fields[F_OPEN],
            "high": fields[F_HIGH],
            "low": fields[F_LOW],
            "volume": fields[F_VOLUME],
        }

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    async def run(self, stock_codes: list[str]) -> None:
        """Connect, subscribe, and stream prices indefinitely.

        Reconnects automatically on disconnection.
        """
        while True:
            try:
                await self._connect_and_stream(stock_codes)
            except Exception as e:
                logger.warning("KIS WebSocket disconnected: %s. Reconnecting in 5s...", e)
                self._ws = None
                self._subscribed.clear()
                await asyncio.sleep(5)

    async def _connect_and_stream(self, stock_codes: list[str]) -> None:
        """Single connection lifecycle: connect, subscribe, read messages."""
        approval_key = await self._get_approval_key()
        ws_url = self.config.kis_ws_url

        logger.info("Connecting to KIS WebSocket: %s", ws_url)

        async with ws_connect(ws_url, ping_interval=30) as ws:
            self._ws = ws
            logger.info("KIS WebSocket connected")

            # Subscribe to all watchlist stocks
            await self.subscribe(stock_codes)

            # Read messages
            async for message in ws:
                if isinstance(message, bytes):
                    message = message.decode("utf-8", errors="replace")

                # Try to parse as price data
                price = self._parse_price_message(message)
                if price and self.on_price:
                    try:
                        await self.on_price(price)
                    except Exception as e:
                        logger.error("Price callback error: %s", e)

    async def close(self) -> None:
        """Close the WebSocket connection."""
        if self._ws:
            await self._ws.close()
            self._ws = None
            logger.info("KIS WebSocket closed")
