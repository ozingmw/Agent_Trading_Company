"""Artifact contracts and payload schemas."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, field_validator, model_validator


class Role(str, Enum):
    COLLECTOR = "collector"
    ANALYST = "analyst"
    CRITIC = "critic"
    EXECUTOR = "executor"
    PORTFOLIO = "portfolio"
    JUDGE = "judge"
    ORCHESTRATOR = "orchestrator"


class Status(str, Enum):
    WORKING = "working"
    COMPLETED = "completed"
    ERROR = "error"


class CollectorPayload(BaseModel):
    sources: list[str]
    universe: str
    counts: dict[str, int]
    outputs_by_source: dict[str, str]


class AnalystPayload(BaseModel):
    symbol: str
    exchange: str
    side: str
    order_type: str
    limit_price: float | None
    size_hint: float
    confidence: float


class CriticPayload(BaseModel):
    recommendation: str
    adjustment: dict[str, Any] | None
    notes: str


class ExecutorPayload(BaseModel):
    order_id: str
    status: str
    symbol: str
    critic_recommendation: str


class PortfolioPayload(BaseModel):
    cash: float
    positions_count: int
    pnl_total: float


class JudgePayload(BaseModel):
    leaderboard_top: str
    scores: dict[str, float]
    rationale: str | None = None


class OrchestratorPayload(BaseModel):
    tick_type: str
    tick_at: str


class Artifact(BaseModel):
    artifact_id: str
    agent_id: str
    role: Role
    created_at: str
    inputs: list[str]
    outputs: list[str]
    directive_hash: str
    references: list[str] | None = None
    artifact_kind: str | None = None
    payload: dict[str, Any]
    status: Status

    @field_validator("created_at")
    @classmethod
    def validate_created_at(cls, value: str) -> str:
        _ = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return value

    @model_validator(mode="after")
    def validate_role_payload(self) -> "Artifact":
        payload_any: Any = self.payload
        if self.role == Role.COLLECTOR:
            _ = CollectorPayload.model_validate(payload_any)
        elif self.role == Role.ANALYST:
            _ = AnalystPayload.model_validate(payload_any)
        elif self.role == Role.CRITIC:
            _ = CriticPayload.model_validate(payload_any)
        elif self.role == Role.EXECUTOR:
            _ = ExecutorPayload.model_validate(payload_any)
        elif self.role == Role.PORTFOLIO:
            _ = PortfolioPayload.model_validate(payload_any)
        elif self.role == Role.JUDGE:
            _ = JudgePayload.model_validate(payload_any)
        elif self.role == Role.ORCHESTRATOR:
            _ = OrchestratorPayload.model_validate(payload_any)
        return self


def validate_artifact(data: dict[str, Any]) -> Artifact:
    return Artifact.model_validate(data)
