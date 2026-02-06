from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse

from atc.audit import AuditLog
from atc.events import EventBus
from atc.types import AgentStatus


@dataclass
class AppState:
    bus: EventBus
    audit: AuditLog
    broker: Any
    registry: Any
    universe_manager: Any


def create_app(state: AppState) -> FastAPI:
    app = FastAPI(title="Agent Trading Company")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/")
    def root() -> dict:
        return {
            "status": "ok",
            "message": "ATC API is running.",
            "docs": "/docs",
            "health": "/api/health",
            "dashboard": "http://localhost:5173",
        }

    @app.get("/favicon.ico")
    def favicon() -> Response:
        return Response(status_code=204)

    @app.get("/api/positions")
    def positions() -> dict:
        return {"positions": state.broker.get_positions()}

    @app.get("/api/orders")
    def orders() -> dict:
        if hasattr(state.broker, "get_orders"):
            return {"orders": [o.__dict__ if hasattr(o, "__dict__") else o for o in state.broker.get_orders()]}
        return {"orders": []}

    @app.get("/api/pnl")
    def pnl() -> dict:
        account = state.broker.get_account()
        market_value = 0.0
        if hasattr(state.broker, "last_prices"):
            for symbol, qty in account.positions.items():
                price = state.broker.last_prices.get(symbol, 0.0)
                market_value += price * qty
        return {
            "cash": account.cash,
            "market_value": market_value,
            "equity": account.cash + market_value,
        }

    @app.get("/api/agents/status")
    def agent_status() -> dict:
        statuses = state.registry.get_statuses()
        return {
            "agents": {
                name: status.model_dump() if isinstance(status, AgentStatus) else status
                for name, status in statuses.items()
            }
        }

    @app.get("/api/audit/latest")
    def audit_latest() -> dict:
        return {"events": state.audit.latest_events()}

    @app.get("/api/universe")
    def universe() -> dict:
        snapshot = state.universe_manager.snapshot()
        return {
            "symbols_kr": snapshot.symbols_kr,
            "symbols_us": snapshot.symbols_us,
            "trends": snapshot.trends,
        }

    @app.get("/api/stream")
    async def stream() -> StreamingResponse:
        queue = await state.bus.subscribe("*")

        async def event_generator():
            while True:
                event = await queue.get()
                payload = {
                    "type": event.type,
                    "source": event.source,
                    "ts": event.ts.isoformat(timespec="seconds") + "Z",
                    "cycle_id": event.cycle_id,
                    "payload": event.payload,
                }
                safe_payload = jsonable_encoder(payload)
                yield f"data: {json.dumps(safe_payload)}\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    return app
