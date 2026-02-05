from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import List, Literal, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field


class AppSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cycle_seconds: int = 60
    session_check_seconds: int = 60
    log_level: str = "INFO"


class MarketsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enable_kr: bool = True
    enable_us: bool = True


class KisConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["paper", "live"] = "paper"
    base_url: str
    token_url_paper: str
    token_url_live: str
    app_key_env: str
    app_secret_env: str
    account_env: str


class DataSourcesConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    newsapi_enabled: bool = True
    newsapi_api_key_env: str
    newsapi_query: str
    newsapi_language: str
    naver_rss: List[str] = Field(default_factory=list)
    daum_rss: List[str] = Field(default_factory=list)
    reddit_enabled: bool = True
    reddit_subreddits: List[str] = Field(default_factory=list)
    reddit_user_agent: str = "atc-bot/0.1"


class LLMConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str = "openai"
    model: str = "gpt-4o-mini"
    temperature: float = 0.2


class UniverseConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    seed_symbols_kr: List[str] = Field(default_factory=list)
    seed_symbols_us: List[str] = Field(default_factory=list)
    max_symbols: int = 50


class DashboardConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    host: str = "0.0.0.0"
    port: int = 8000


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    app: AppSettings
    markets: MarketsConfig
    kis: KisConfig
    data_sources: DataSourcesConfig
    llm: LLMConfig
    universe: UniverseConfig
    dashboard: DashboardConfig


class Secrets(BaseModel):
    model_config = ConfigDict(extra="forbid")

    openai_api_key: Optional[str] = None
    kis_app_key: Optional[str] = None
    kis_app_secret: Optional[str] = None
    kis_account_no: Optional[str] = None
    newsapi_key: Optional[str] = None


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path)
    with config_path.open("rb") as handle:
        data = tomllib.load(handle)
    return AppConfig.model_validate(data)


def load_secrets(config: AppConfig) -> Secrets:
    load_dotenv()
    return Secrets(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        kis_app_key=os.getenv(config.kis.app_key_env),
        kis_app_secret=os.getenv(config.kis.app_secret_env),
        kis_account_no=os.getenv(config.kis.account_env),
        newsapi_key=os.getenv(config.data_sources.newsapi_api_key_env),
    )
