"""
Pydantic v2 models for KIS Open API responses.

Field names follow the KIS API response schema exactly.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

class TokenResponse(BaseModel):
    """OAuth2 token response from /oauth2/tokenP."""

    access_token: str
    token_type: str = "Bearer"
    expires_in: int


# ---------------------------------------------------------------------------
# Market data
# ---------------------------------------------------------------------------

class StockPrice(BaseModel):
    """Current stock quote from inquire-price."""

    stck_prpr: str = Field(description="Current price")
    stck_oprc: str = Field(description="Open price")
    stck_hgpr: str = Field(description="High price")
    stck_lwpr: str = Field(description="Low price")
    acml_vol: str = Field(description="Accumulated volume")
    prdy_ctrt: str = Field(description="Previous-day change rate (%)")
    prdy_vrss: str = Field(default="", description="Previous-day change amount")
    prdy_vrss_sign: str = Field(default="", description="Previous-day change sign")
    stck_mxpr: str = Field(default="", description="Upper limit price")
    stck_llam: str = Field(default="", description="Lower limit price")

    class Config:
        extra = "allow"


class DailyPrice(BaseModel):
    """Single-day OHLCV entry from inquire-daily-price."""

    stck_bsop_date: str = Field(description="Business date (YYYYMMDD)")
    stck_oprc: str = Field(description="Open price")
    stck_hgpr: str = Field(description="High price")
    stck_lwpr: str = Field(description="Low price")
    stck_clpr: str = Field(description="Close price")
    acml_vol: str = Field(description="Accumulated volume")
    prdy_ctrt: str = Field(default="", description="Previous-day change rate (%)")

    class Config:
        extra = "allow"


# ---------------------------------------------------------------------------
# Order
# ---------------------------------------------------------------------------

class OrderOutput(BaseModel):
    """Nested output block inside an order response."""

    KRX_FWDG_ORD_ORGNO: str = Field(default="", description="KRX forwarding order org number")
    ODNO: str = Field(default="", description="Order number")
    ORD_TMD: str = Field(default="", description="Order time")


class OrderResponse(BaseModel):
    """Response from order-cash (buy/sell)."""

    rt_cd: str = Field(description="Return code ('0' = success)")
    msg_cd: str = Field(description="Message code")
    msg1: str = Field(description="Message text")
    output: OrderOutput | None = None


# ---------------------------------------------------------------------------
# Balance
# ---------------------------------------------------------------------------

class BalanceItem(BaseModel):
    """Single holding entry from inquire-balance output1."""

    pdno: str = Field(description="Product number (stock code)")
    prdt_name: str = Field(description="Product name")
    hldg_qty: str = Field(description="Holding quantity")
    pchs_avg_pric: str = Field(description="Average purchase price")
    prpr: str = Field(description="Current price")
    evlu_pfls_amt: str = Field(description="Evaluated P&L amount")
    evlu_pfls_rt: str = Field(description="Evaluated P&L rate (%)")

    class Config:
        extra = "allow"


class AccountBalance(BaseModel):
    """Aggregated account balance from inquire-balance."""

    items: list[BalanceItem] = Field(default_factory=list, description="Individual holdings")
    total_evlu_amt: str = Field(default="0", description="Total evaluation amount")
    total_evlu_pfls_amt: str = Field(default="0", description="Total evaluated P&L amount")
