from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo


KR_TZ = ZoneInfo("Asia/Seoul")
US_TZ = ZoneInfo("America/New_York")


def _is_weekday(dt: datetime) -> bool:
    return dt.weekday() < 5


def is_market_open_kr(now: datetime | None = None) -> bool:
    now = now or datetime.now(tz=KR_TZ)
    if not _is_weekday(now):
        return False
    start = time(9, 0)
    end = time(15, 30)
    return start <= now.time() <= end


def is_market_open_us(now: datetime | None = None) -> bool:
    now = now or datetime.now(tz=US_TZ)
    if not _is_weekday(now):
        return False
    start = time(9, 30)
    end = time(16, 0)
    return start <= now.time() <= end
