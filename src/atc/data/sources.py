from __future__ import annotations

from datetime import datetime
from typing import Iterable, List, Optional

import feedparser
import requests

from atc.types import NewsItem, SocialPost


def fetch_rss_news(urls: Iterable[str], source: str) -> List[NewsItem]:
    items: List[NewsItem] = []
    for url in urls:
        parsed = feedparser.parse(url)
        for entry in parsed.entries[:20]:
            published = None
            if "published_parsed" in entry and entry.published_parsed:
                published = datetime(*entry.published_parsed[:6])
            items.append(
                NewsItem(
                    source=source,
                    title=entry.get("title", ""),
                    url=entry.get("link", ""),
                    published_at=published,
                )
            )
    return items


def fetch_newsapi(api_key: Optional[str], query: str, language: str) -> List[NewsItem]:
    if not api_key:
        return []
    url = "https://newsapi.org/v2/everything"
    params = {"q": query, "language": language, "pageSize": 20}
    headers = {"X-Api-Key": api_key}
    resp = requests.get(url, params=params, headers=headers, timeout=10)
    if resp.status_code != 200:
        return []
    data = resp.json()
    results = []
    for article in data.get("articles", [])[:20]:
        published = None
        if article.get("publishedAt"):
            try:
                published = datetime.fromisoformat(
                    article["publishedAt"].replace("Z", "+00:00")
                )
            except ValueError:
                published = None
        results.append(
            NewsItem(
                source="NewsAPI",
                title=article.get("title") or "",
                url=article.get("url") or "",
                published_at=published,
            )
        )
    return results


def fetch_reddit_posts(
    subreddits: Iterable[str], user_agent: str, limit: int = 10
) -> List[SocialPost]:
    posts: List[SocialPost] = []
    headers = {"User-Agent": user_agent}
    for sub in subreddits:
        url = f"https://www.reddit.com/r/{sub}/new.json"
        params = {"limit": limit}
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        if resp.status_code != 200:
            continue
        payload = resp.json()
        for child in payload.get("data", {}).get("children", [])[:limit]:
            data = child.get("data", {})
            posts.append(
                SocialPost(
                    source=f"reddit/{sub}",
                    title=data.get("title", ""),
                    url=f"https://reddit.com{data.get('permalink', '')}",
                    score=data.get("score"),
                    published_at=datetime.utcfromtimestamp(data.get("created_utc", 0)),
                )
            )
    return posts
