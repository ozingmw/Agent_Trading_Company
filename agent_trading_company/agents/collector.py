from __future__ import annotations

import csv
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import requests
import yaml
from bs4 import BeautifulSoup

from agent_trading_company.core.directives import compute_directive_hash
from agent_trading_company.io.atomic_writer import atomic_write
from agent_trading_company.kis.client import KISClient, MissingEnvError
from agent_trading_company.llm.router import get_router
from agent_trading_company.storage.store import Store


@dataclass(frozen=True)
class UniverseEntry:
    symbol: str
    exchange: str


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _iso_ts(value: datetime) -> str:
    return value.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_universe(path: Path) -> list[UniverseEntry]:
    entries = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            entries.append(UniverseEntry(symbol=row["symbol"], exchange=row["exchange"]))
    return entries


def _write_jsonl(path: Path, rows: Iterable[dict]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(row, ensure_ascii=False) for row in rows]
    content = "\n".join(lines) + ("\n" if lines else "")
    atomic_write(path, content)
    return len(lines)


def _write_jsonl_with_checksum(path: Path, rows: Iterable[dict]) -> tuple[int, str]:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(row, ensure_ascii=False) for row in rows]
    content = "\n".join(lines) + ("\n" if lines else "")
    atomic_write(path, content)
    checksum = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return len(lines), checksum


def _load_corp_codes(path: Path) -> dict[str, str]:
    codes: dict[str, str] = {}
    if not path.exists():
        return codes
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            codes[row["symbol"]] = row["corp_code"]
    return codes


def _budget_path() -> Path:
    return Path("state/data_budget.json")


def _load_budget(now: datetime, cap: int) -> dict:
    path = _budget_path()
    date_key = now.strftime("%Y-%m-%d")
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("date") == date_key:
            return data
    return {"date": date_key, "cap": cap, "used_total": 0, "used_by_source": {}}


def _save_budget(data: dict) -> None:
    path = _budget_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(path, json.dumps(data, indent=2))


def _consume_budget(data: dict, source: str, cost: int = 1) -> bool:
    if data["used_total"] + cost > data["cap"]:
        return False
    data["used_total"] += cost
    data["used_by_source"][source] = data["used_by_source"].get(source, 0) + cost
    return True


def _parse_naver_news(html: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "lxml")
    items = []
    for link in soup.select(".main_news .newsList li a"):
        title = link.get_text(strip=True)
        href = link.get("href")
        if not title or not href:
            continue
        url = href if href.startswith("http") else f"https://finance.naver.com{href}"
        items.append({"title": title, "url": url})
    return items


def _parse_naver_board(html: str, symbol: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "lxml")
    items = []
    for link in soup.select(".type2 tbody tr td.title a"):
        title = link.get_text(strip=True)
        href = link.get("href")
        if not title or not href:
            continue
        url = href if href.startswith("http") else f"https://finance.naver.com{href}"
        items.append({"symbol": symbol, "title": title, "url": url})
    return items


def _artifact_path(now: datetime) -> Path:
    name = f"{now.strftime('%Y%m%d_%H%M%SZ')}_collector-1_collector_c1.md"
    return Path("artifacts/collector") / name


def _error_artifact(now: datetime, message: str) -> Path:
    path = Path("artifacts/collector") / f"error_{now.strftime('%Y%m%d_%H%M%SZ')}.md"
    front_matter = {
        "artifact_id": f"err-{now.strftime('%Y%m%d-%H%M%S')}",
        "agent_id": "collector-1",
        "role": "collector",
        "created_at": _iso_ts(now),
        "inputs": [],
        "outputs": [],
        "directive_hash": "",
        "payload": {
            "sources": [],
            "universe": "",
            "counts": {},
            "outputs_by_source": {},
        },
        "status": "error",
    }
    front_text = yaml.safe_dump(front_matter, sort_keys=False).strip()
    content = f"---\n{front_text}\n---\nCollector error: {message}\n"
    atomic_write(path, content)
    return path


def run(artifact_path: str, directives: dict, store: Store) -> str:
    now = _now_utc()
    directives_path = Path("directives/admin_directives.md")
    directive_hash = compute_directive_hash(directives_path.read_text(encoding="utf-8"))

    market_universe = str(directives.get("market_universe", "KRX"))
    universe_file = Path(str(directives.get("symbol_universe_file", "config/universe.csv")))
    entries = _load_universe(universe_file)

    sources = list(directives.get("data_sources_enabled", ["kis", "naver_finance"]))
    outputs_by_source: dict[str, str] = {}
    counts: dict[str, int] = {source: 0 for source in sources}

    cap = int(directives.get("data_budget_cap", 1000))
    budget = _load_budget(now, cap)

    date_path = now.strftime("%Y%m%d")
    rows = []
    kis_client = None
    if "kis" in sources:
        try:
            kis_client = KISClient.from_env()
        except MissingEnvError as exc:
            _error_artifact(now, str(exc))
            sources.remove("kis")

    router = get_router()
    budget_remaining = max(budget["cap"] - budget["used_total"], 0)
    plan = router.invoke(
        "collector_plan",
        {
            "market_universe": market_universe,
            "enabled_sources": sources,
            "budget_remaining": budget_remaining,
            "has_kis": kis_client is not None,
            "has_dart": bool(os.getenv("DART_API_KEY")),
        },
    )
    sources = list(plan.get("sources", sources))

    for entry in entries:
        if market_universe.upper() == "OVERSEAS" and entry.exchange not in ("NASD", "NYSE", "AMEX"):
            continue
        if market_universe.upper() == "KRX" and entry.exchange != "KRX":
            continue
        if "kis" in sources and kis_client is not None:
            if not _consume_budget(budget, "kis"):
                _error_artifact(now, "data budget exceeded for kis")
                break
            if market_universe.upper() == "KRX":
                response = kis_client.inquire_domestic_price("J", entry.symbol)
                price = response.get("output", {}).get("stck_prpr")
            else:
                response = kis_client.inquire_overseas_price(entry.exchange, entry.symbol)
                price = response.get("output", {}).get("last")
            rows.append(
                {
                    "ts": _iso_ts(now),
                    "source": "kis",
                    "symbol": entry.symbol,
                    "exchange": entry.exchange,
                    "price": price,
                    "raw": response,
                }
            )

    if rows and "kis" in sources:
        kis_path = Path("data/raw") / date_path / "kis_quotes.jsonl"
        counts["kis"], checksum = _write_jsonl_with_checksum(kis_path, rows)
        outputs_by_source["kis"] = str(kis_path)
        store.register_data(
            "kis",
            str(kis_path),
            {
                "data_id": f"kis-{date_path}",
                "symbol": "*",
                "start_ts": _iso_ts(now),
                "end_ts": _iso_ts(now),
                "format": "jsonl",
                "checksum": checksum,
                "created_at": _iso_ts(now),
            },
        )

    if "naver_finance" in sources:
        if not _consume_budget(budget, "naver_finance"):
            _error_artifact(now, "data budget exceeded for naver_finance")
        else:
            response = requests.get("https://finance.naver.com/news/", timeout=10)
            response.raise_for_status()
            items = _parse_naver_news(response.text)
            news_rows = [
                {
                    "ts": _iso_ts(now),
                    "source": "naver_finance",
                    "title": item["title"],
                    "url": item["url"],
                    "published_at": _iso_ts(now),
                }
                for item in items
            ]
            news_path = Path("data/raw") / date_path / "naver_news.jsonl"
            counts["naver_finance"], checksum = _write_jsonl_with_checksum(news_path, news_rows)
            outputs_by_source["naver_finance"] = str(news_path)
            store.register_data(
                "naver_finance",
                str(news_path),
                {
                    "data_id": f"naver-news-{date_path}",
                    "symbol": "*",
                    "start_ts": _iso_ts(now),
                    "end_ts": _iso_ts(now),
                    "format": "jsonl",
                    "checksum": checksum,
                    "created_at": _iso_ts(now),
                },
            )

    if "naver_board" in sources:
        board_rows = []
        for entry in entries:
            if entry.exchange != "KRX":
                continue
            if not _consume_budget(budget, "naver_board"):
                _error_artifact(now, "data budget exceeded for naver_board")
                break
            response = requests.get(
                f"https://finance.naver.com/item/board.naver?code={entry.symbol}", timeout=10
            )
            response.raise_for_status()
            board_rows.extend(_parse_naver_board(response.text, entry.symbol))
        if board_rows:
            board_path = Path("data/raw") / date_path / "naver_board.jsonl"
            counts["naver_board"], checksum = _write_jsonl_with_checksum(board_path, board_rows)
            outputs_by_source["naver_board"] = str(board_path)
            store.register_data(
                "naver_board",
                str(board_path),
                {
                    "data_id": f"naver-board-{date_path}",
                    "symbol": "*",
                    "start_ts": _iso_ts(now),
                    "end_ts": _iso_ts(now),
                    "format": "jsonl",
                    "checksum": checksum,
                    "created_at": _iso_ts(now),
                },
            )

    if "dart" in sources:
        if not _consume_budget(budget, "dart"):
            _error_artifact(now, "data budget exceeded for dart")
        else:
            dart_key = os.getenv("DART_API_KEY")
            if not dart_key:
                _error_artifact(now, "missing DART_API_KEY")
            else:
                corp_codes = _load_corp_codes(Path("config/corp_code_map.csv"))
                dart_rows = []
                for entry in entries:
                    if entry.exchange != "KRX":
                        continue
                    corp_code = corp_codes.get(entry.symbol)
                    if not corp_code:
                        continue
                    response = requests.get(
                        "https://opendart.fss.or.kr/api/list.json",
                        params={"crtfc_key": dart_key, "corp_code": corp_code, "page_count": 10},
                        timeout=10,
                    )
                    response.raise_for_status()
                    data = response.json()
                    for item in data.get("list", [])[:10]:
                        dart_rows.append(
                            {
                                "ts": _iso_ts(now),
                                "source": "dart",
                                "corp_code": corp_code,
                                "report_nm": item.get("report_nm"),
                                "rcept_no": item.get("rcept_no"),
                                "rcept_dt": item.get("rcept_dt"),
                            }
                        )
                if dart_rows:
                    dart_path = Path("data/raw") / date_path / "dart_list.jsonl"
                    counts["dart"], checksum = _write_jsonl_with_checksum(dart_path, dart_rows)
                    outputs_by_source["dart"] = str(dart_path)
                    store.register_data(
                        "dart",
                        str(dart_path),
                        {
                            "data_id": f"dart-{date_path}",
                            "symbol": "*",
                            "start_ts": _iso_ts(now),
                            "end_ts": _iso_ts(now),
                            "format": "jsonl",
                            "checksum": checksum,
                            "created_at": _iso_ts(now),
                        },
                    )

    _save_budget(budget)

    artifact_path_obj = _artifact_path(now)
    front_matter = {
        "artifact_id": f"c1-{now.strftime('%Y%m%d-%H%M%S')}",
        "agent_id": "collector-1",
        "role": "collector",
        "created_at": _iso_ts(now),
        "inputs": [],
        "outputs": list(outputs_by_source.values()),
        "directive_hash": directive_hash,
        "payload": {
            "sources": sources,
            "universe": market_universe,
            "counts": counts,
            "outputs_by_source": outputs_by_source,
        },
        "status": "completed",
    }
    front_text = yaml.safe_dump(front_matter, sort_keys=False).strip()
    content = (
        f"---\n{front_text}\n---\n"
        f"Collected KIS quotes for universe={market_universe}. {counts.get('kis', 0)} symbols.\n"
    )
    atomic_write(artifact_path_obj, content)
    return str(artifact_path_obj)
