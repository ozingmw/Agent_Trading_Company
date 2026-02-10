"""
Central configuration module for Agent Trading Company.
Loads environment variables and exposes a Config dataclass with validated settings.
"""

import os
import json
from dataclasses import dataclass, field
from typing import List
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
load_dotenv()

WATCHLIST_FILE = Path(__file__).parent / "watchlist.json"


@dataclass
class Config:
    """Application configuration loaded from environment variables."""

    # Trading mode
    trading_mode: str = field(default_factory=lambda: os.getenv("TRADING_MODE", "paper"))

    # KIS API credentials (computed based on trading_mode)
    kis_app_key: str = field(init=False)
    kis_app_secret: str = field(init=False)
    kis_account_no: str = field(init=False)
    kis_acnt_prdt_cd: str = "01"
    kis_base_url: str = field(init=False)
    kis_ws_url: str = field(init=False)

    # OpenAI credentials
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    openai_model: str = field(init=False)

    # Agent configuration
    watchlist: List[str] = field(default_factory=lambda: _parse_watchlist())
    data_collector_interval: int = field(default_factory=lambda: int(os.getenv("DATA_COLLECTOR_INTERVAL", "60")))
    data_analyst_interval: int = field(default_factory=lambda: int(os.getenv("DATA_ANALYST_INTERVAL", "120")))
    trade_executor_interval: int = field(default_factory=lambda: int(os.getenv("TRADE_EXECUTOR_INTERVAL", "180")))
    risk_manager_interval: int = field(default_factory=lambda: int(os.getenv("RISK_MANAGER_INTERVAL", "90")))

    # API server configuration
    api_port: int = field(default_factory=lambda: int(os.getenv("API_PORT", "8000")))
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))

    def __post_init__(self):
        """Compute derived fields based on trading_mode."""
        mode = self.trading_mode.lower()

        if mode == "paper":
            self.kis_app_key = os.getenv("KIS_PAPER_APP_KEY", "")
            self.kis_app_secret = os.getenv("KIS_PAPER_APP_SECRET", "")
            account_full = os.getenv("KIS_PAPER_ACCOUNT_NO", "")
            self.kis_account_no = account_full[:8] if len(account_full) >= 8 else account_full
            self.kis_base_url = "https://openapivts.koreainvestment.com:29443"
            self.kis_ws_url = "ws://ops.koreainvestment.com:31000"
            self.openai_model = os.getenv("OPENAI_MODEL_PAPER", "gpt-5-mini")
        elif mode == "live":
            self.kis_app_key = os.getenv("KIS_LIVE_APP_KEY", "")
            self.kis_app_secret = os.getenv("KIS_LIVE_APP_SECRET", "")
            account_full = os.getenv("KIS_LIVE_ACCOUNT_NO", "")
            self.kis_account_no = account_full[:8] if len(account_full) >= 8 else account_full
            self.kis_base_url = "https://openapi.koreainvestment.com:9443"
            self.kis_ws_url = "ws://ops.koreainvestment.com:21000"
            self.openai_model = os.getenv("OPENAI_MODEL_LIVE", "gpt-5-mini")
        else:
            raise ValueError(f"Invalid TRADING_MODE: {self.trading_mode}. Must be 'paper' or 'live'.")

    def validate(self) -> None:
        """
        Validate that all required configuration fields are present.
        Raises ValueError if any required field is missing or invalid.
        """
        errors = []

        # Check trading mode
        if self.trading_mode not in ["paper", "live"]:
            errors.append(f"Invalid trading_mode: {self.trading_mode}")

        # Check KIS credentials
        if not self.kis_app_key:
            errors.append(f"Missing KIS_{'PAPER' if self.trading_mode == 'paper' else 'LIVE'}_APP_KEY")
        if not self.kis_app_secret:
            errors.append(f"Missing KIS_{'PAPER' if self.trading_mode == 'paper' else 'LIVE'}_APP_SECRET")
        if not self.kis_account_no:
            errors.append(f"Missing KIS_{'PAPER' if self.trading_mode == 'paper' else 'LIVE'}_ACCOUNT_NO")

        # Check OpenAI credentials
        if not self.openai_api_key:
            errors.append("Missing OPENAI_API_KEY")
        if not self.openai_model:
            errors.append(f"Missing OPENAI_MODEL_{'PAPER' if self.trading_mode == 'paper' else 'LIVE'}")

        # Check watchlist
        if not self.watchlist:
            errors.append("Watchlist is empty")

        # Check intervals are positive
        if self.data_collector_interval <= 0:
            errors.append("data_collector_interval must be positive")
        if self.data_analyst_interval <= 0:
            errors.append("data_analyst_interval must be positive")
        if self.trade_executor_interval <= 0:
            errors.append("trade_executor_interval must be positive")
        if self.risk_manager_interval <= 0:
            errors.append("risk_manager_interval must be positive")

        if errors:
            raise ValueError("Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors))


def _load_watchlist_file() -> List[str] | None:
    """Load watchlist from JSON file. Returns None if file doesn't exist."""
    if WATCHLIST_FILE.exists():
        try:
            data = json.loads(WATCHLIST_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list) and all(isinstance(s, str) for s in data):
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return None


def _save_watchlist_file(watchlist: List[str]) -> None:
    """Persist watchlist to JSON file."""
    WATCHLIST_FILE.write_text(json.dumps(watchlist, indent=2, ensure_ascii=False), encoding="utf-8")


def _parse_watchlist() -> List[str]:
    """Load watchlist with priority: file > env var > defaults."""
    # 1. Try file first
    from_file = _load_watchlist_file()
    if from_file is not None:
        return from_file

    # 2. Try environment variable
    watchlist_str = os.getenv("AGENT_WATCHLIST", "")
    if watchlist_str:
        watchlist = [code.strip() for code in watchlist_str.split(",") if code.strip()]
    else:
        # 3. Defaults (Samsung, SK Hynix, NAVER, Kakao, LG Chem)
        watchlist = ["005930", "000660", "035420", "035720", "051910"]

    # Auto-create file so it becomes the single source of truth
    _save_watchlist_file(watchlist)
    return watchlist


# Global config instance
config = Config()
