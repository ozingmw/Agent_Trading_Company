from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import re
import asyncio
from agents.report import ReportManager
from agents.market_schedule import get_market_status

router = APIRouter(prefix="/api")

# These will be set by app.py
_agents = []
_kis_client = None
_config = None
_kis_ws = None


def set_kis_ws(kis_ws):
    global _kis_ws
    _kis_ws = kis_ws


class WatchlistAddRequest(BaseModel):
    stock_code: str

def init_routes(agents, kis_client, config):
    global _agents, _kis_client, _config
    _agents = agents
    _kis_client = kis_client
    _config = config

@router.get("/watchlist")
async def get_watchlist():
    """Return the current watchlist."""
    if not _config:
        raise HTTPException(503, "Config not available")
    return _config.watchlist


@router.post("/watchlist")
async def add_to_watchlist(req: WatchlistAddRequest):
    """Add a stock code to the watchlist."""
    if not _config:
        raise HTTPException(503, "Config not available")

    code = req.stock_code.strip()
    if not re.fullmatch(r"\d{6}", code):
        raise HTTPException(400, "Stock code must be exactly 6 digits")
    if code in _config.watchlist:
        raise HTTPException(409, f"{code} is already in the watchlist")

    _config.watchlist.append(code)

    from config import _save_watchlist_file
    _save_watchlist_file(_config.watchlist)

    # Subscribe to real-time prices if WebSocket is available
    if _kis_ws:
        asyncio.create_task(_kis_ws.subscribe([code]))

    return {"watchlist": _config.watchlist}


@router.delete("/watchlist/{stock_code}")
async def remove_from_watchlist(stock_code: str):
    """Remove a stock code from the watchlist."""
    if not _config:
        raise HTTPException(503, "Config not available")

    if stock_code not in _config.watchlist:
        raise HTTPException(404, f"{stock_code} is not in the watchlist")

    _config.watchlist.remove(stock_code)

    from config import _save_watchlist_file
    _save_watchlist_file(_config.watchlist)

    return {"watchlist": _config.watchlist}

@router.get("/agents")
async def get_agents():
    return [agent.get_status() for agent in _agents]

@router.get("/agents/{name}")
async def get_agent(name: str):
    agent = next((a for a in _agents if a.name == name), None)
    if not agent:
        raise HTTPException(404, f"Agent {name} not found")
    return agent.get_status()

@router.get("/reports")
async def get_all_reports(limit: int = 30):
    """Get all reports from all agents in reverse chronological order."""
    from pathlib import Path
    agent_names = ["data_collector", "data_analyst", "trade_executor", "risk_manager"]
    all_reports = []
    rm = ReportManager("_")  # Just to get reports_dir
    for agent_name in agent_names:
        agent_dir = rm.reports_dir / agent_name
        if not agent_dir.exists():
            continue
        for filepath in agent_dir.glob("*.md"):
            all_reports.append({
                "filename": filepath.name,
                "agent": agent_name,
                "content": filepath.read_text(encoding="utf-8"),
            })
    # Sort by filename (which is timestamp-based) in reverse chronological order
    all_reports.sort(key=lambda r: r["filename"], reverse=True)
    return all_reports[:limit]

@router.get("/agents/{name}/reports")
async def get_agent_reports(name: str, limit: int = 10):
    rm = ReportManager(name)
    filenames = rm.list_reports(name)[:limit]
    return [{"filename": f, "agent": name} for f in filenames]

@router.get("/agents/{name}/reports/{filename}")
async def get_report_content(name: str, filename: str):
    rm = ReportManager(name)
    from pathlib import Path
    filepath = rm.reports_dir / name / filename
    if not filepath.exists():
        raise HTTPException(404, "Report not found")
    return {"filename": filename, "agent": name, "content": filepath.read_text(encoding="utf-8")}

@router.get("/trades")
async def get_trades(limit: int = 20):
    """Get recent trades from executor reports."""
    import json
    import re

    rm = ReportManager("trade_executor")
    agent_dir = rm.reports_dir / "trade_executor"

    if not agent_dir.exists():
        return []

    trades = []

    # Scan ALL report files (sorted newest first) and collect actual trades
    report_files = sorted(agent_dir.glob("*.md"), reverse=True)

    for filepath in report_files:
        try:
            filename = filepath.stem
            parts = filename.split("_")
            if len(parts) == 2:
                date_part = parts[0]
                time_part = parts[1].replace("-", ":")
                timestamp_iso = f"{date_part}T{time_part}"
            else:
                continue

            content = filepath.read_text(encoding="utf-8")

            data_match = re.search(r'## Data\n(.*?)\n\n##', content, re.DOTALL)
            if not data_match:
                continue

            data_section = data_match.group(1).strip()
            if not data_section or data_section == "[]":
                continue

            orders_data = json.loads(data_section)

            for item in orders_data:
                order = item.get("order", {})
                result = item.get("result", "failed")

                status_map = {
                    "success": "filled",
                    "failed": "failed",
                    "skipped": "failed",
                }
                trade = {
                    "timestamp": timestamp_iso,
                    "stock_code": order.get("stock_code", ""),
                    "stock_name": order.get("stock_code", ""),
                    "action": order.get("action", "buy"),
                    "qty": order.get("qty", 0),
                    "price": order.get("price", 0),
                    "status": status_map.get(result, "failed"),
                }
                trades.append(trade)

        except (json.JSONDecodeError, ValueError, KeyError):
            continue

        # Stop scanning once we have enough trades
        if len(trades) >= limit:
            break

    trades.sort(key=lambda t: t["timestamp"], reverse=True)
    return trades[:limit]

@router.get("/balance")
async def get_balance():
    if not _kis_client:
        raise HTTPException(503, "KIS client not available")
    try:
        balance = await _kis_client.get_balance()
        return balance.model_dump()
    except Exception as e:
        raise HTTPException(500, str(e))

@router.get("/config")
async def get_config():
    return {
        "trading_mode": _config.trading_mode,
        "openai_model": _config.openai_model,
        "watchlist": _config.watchlist,
        "intervals": {
            "data_collector": _config.data_collector_interval,
            "data_analyst": _config.data_analyst_interval,
            "trade_executor": _config.trade_executor_interval,
            "risk_manager": _config.risk_manager_interval,
        }
    }

@router.get("/prices")
async def get_prices():
    """Get current prices for all stocks in the watchlist (sequential to avoid rate limits)."""
    if not _kis_client:
        raise HTTPException(503, "KIS client not available")
    if not _config:
        raise HTTPException(503, "Config not available")

    prices = []
    for stock_code in _config.watchlist:
        try:
            result = await _kis_client.get_price(stock_code)
            prices.append({
                "stock_code": stock_code,
                "price": result.stck_prpr,
                "open": result.stck_oprc,
                "high": result.stck_hgpr,
                "low": result.stck_lwpr,
                "volume": result.acml_vol,
                "change_rate": result.prdy_ctrt,
                "change_amount": result.prdy_vrss,
                "change_sign": result.prdy_vrss_sign,
            })
        except Exception:
            continue

    return prices

@router.get("/market-status")
async def market_status():
    """Get current open/closed status for KR and US markets."""
    return get_market_status()
