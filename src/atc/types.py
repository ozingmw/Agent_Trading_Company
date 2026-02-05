from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

Market = Literal["KR", "US"]
OrderSide = Literal["BUY", "SELL"]
OrderType = Literal["MARKET", "LIMIT"]


class NewsItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str
    title: str
    url: str
    published_at: Optional[datetime] = None


class SocialPost(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str
    title: str
    url: str
    score: Optional[int] = None
    published_at: Optional[datetime] = None


class MarketDataSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quotes: Dict[str, float] = Field(default_factory=dict)
    news: List[NewsItem] = Field(default_factory=list)
    social: List[SocialPost] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)


class SignalIntent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    market: Market
    action: Literal["BUY", "SELL", "HOLD"]
    confidence: float = Field(ge=0.0, le=1.0)
    horizon: str
    order_type: OrderType
    limit_price: Optional[float] = None
    size: int = Field(ge=0)
    rationale: str
    data_used: List[str] = Field(default_factory=list)


class SignalBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intents: List[SignalIntent] = Field(default_factory=list)


class OrderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    market: Market
    side: OrderSide
    quantity: int = Field(ge=1)
    order_type: OrderType
    limit_price: Optional[float] = None
    rationale: str


class OrderResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    market: Market
    side: OrderSide
    quantity: int
    status: str
    broker_order_id: Optional[str] = None
    filled_price: Optional[float] = None


class AgentStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    state: str
    last_action: Optional[str] = None
    last_error: Optional[str] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CriticFeedback(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent: str
    cycle_id: str
    score: float = Field(ge=0.0, le=1.0)
    notes: str


class GuidelineProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target: str
    title: str
    content: str
    proposer: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AccountSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cash: float
    positions: Dict[str, int] = Field(default_factory=dict)
