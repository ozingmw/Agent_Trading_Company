from __future__ import annotations

import re
from collections import Counter
from typing import Iterable, List

from atc.config import AppConfig, Secrets
from atc.data.sources import fetch_newsapi, fetch_reddit_posts, fetch_rss_news
from atc.types import MarketDataSummary


class DataCollector:
    def __init__(self, config: AppConfig, secrets: Secrets, kis_client: object | None) -> None:
        self.config = config
        self.secrets = secrets
        self.kis_client = kis_client

    def collect(self, symbols_kr: Iterable[str], symbols_us: Iterable[str]) -> MarketDataSummary:
        notes: List[str] = []
        quotes = {}
        if self.kis_client and getattr(self.kis_client, "enabled", False):
            try:
                quotes.update(self.kis_client.get_quotes(list(symbols_kr), market="KR"))
                quotes.update(self.kis_client.get_quotes(list(symbols_us), market="US"))
            except Exception as exc:  # noqa: BLE001
                notes.append(f"KIS quote fetch failed: {exc}")
        else:
            notes.append("KIS client not configured; quotes unavailable")

        news_items = []
        social_items = []

        if self.config.data_sources.naver_rss:
            news_items.extend(fetch_rss_news(self.config.data_sources.naver_rss, "Naver"))
        if self.config.data_sources.daum_rss:
            news_items.extend(fetch_rss_news(self.config.data_sources.daum_rss, "Daum"))
        if self.config.data_sources.newsapi_enabled:
            news_items.extend(
                fetch_newsapi(
                    self.secrets.newsapi_key,
                    self.config.data_sources.newsapi_query,
                    self.config.data_sources.newsapi_language,
                )
            )
        if self.config.data_sources.reddit_enabled:
            social_items.extend(
                fetch_reddit_posts(
                    self.config.data_sources.reddit_subreddits,
                    self.config.data_sources.reddit_user_agent,
                )
            )

        trends = self._extract_trends(news_items, social_items)
        return MarketDataSummary(
            quotes=quotes,
            news=news_items,
            social=social_items,
            trends=trends,
            notes=notes,
        )

    def extract_symbol_candidates(self, summary: MarketDataSummary) -> tuple[list[str], list[str]]:
        us_candidates: List[str] = []
        kr_candidates: List[str] = []
        text = " ".join([item.title for item in summary.news + summary.social])

        for match in re.findall(r"\b\d{6}\b", text):
            kr_candidates.append(match)

        for match in re.findall(r"\$?[A-Z]{2,5}\b", text):
            cleaned = match.replace("$", "")
            if cleaned in {"USA", "FED", "ETF", "CEO", "GDP", "CPI", "USD"}:
                continue
            us_candidates.append(cleaned)

        return sorted(set(kr_candidates)), sorted(set(us_candidates))

    def _extract_trends(self, news_items: list, social_items: list) -> List[str]:
        titles = " ".join([item.title for item in news_items + social_items]).lower()
        words = re.findall(r"[a-zA-Z]{3,}", titles)
        stop = {"the", "and", "for", "with", "that", "this", "from", "into", "will", "stock"}
        filtered = [word for word in words if word not in stop]
        counts = Counter(filtered)
        return [word for word, _ in counts.most_common(10)]
