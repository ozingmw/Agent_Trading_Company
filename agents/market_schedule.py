"""
Market schedule utilities for Korean and US stock exchanges.

Determines whether agents should be active based on market hours.
Agents operate during: 30-minute pre-scan + regular trading hours.
Outside these windows, agents sleep.

KR (KRX):  Pre-scan 08:30, Open 09:00, Close 15:30 KST  (weekdays)
US (NYSE): Pre-scan 09:00, Open 09:30, Close 16:00 ET   (weekdays)
"""

from datetime import datetime, time
from enum import Enum
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")
ET = ZoneInfo("America/New_York")


class MarketPhase(str, Enum):
    PRE_SCAN = "pre_scan"
    OPEN = "open"
    CLOSED = "closed"


# KR market times (KST)
KR_PRE_SCAN_START = time(8, 30)
KR_OPEN = time(9, 0)
KR_CLOSE = time(15, 30)

# US market times (ET)
US_PRE_SCAN_START = time(9, 0)
US_OPEN = time(9, 30)
US_CLOSE = time(16, 0)


def _phase(now_time: time, pre_scan: time, mkt_open: time, mkt_close: time) -> MarketPhase:
    """Determine market phase for a given local time."""
    if pre_scan <= now_time < mkt_open:
        return MarketPhase.PRE_SCAN
    if mkt_open <= now_time < mkt_close:
        return MarketPhase.OPEN
    return MarketPhase.CLOSED


def get_kr_phase(now: datetime | None = None) -> MarketPhase:
    """Get current phase of the Korean market."""
    if now is None:
        now = datetime.now(KST)
    else:
        now = now.astimezone(KST)
    # Weekends
    if now.weekday() >= 5:
        return MarketPhase.CLOSED
    return _phase(now.time(), KR_PRE_SCAN_START, KR_OPEN, KR_CLOSE)


def get_us_phase(now: datetime | None = None) -> MarketPhase:
    """Get current phase of the US market."""
    if now is None:
        now = datetime.now(ET)
    else:
        now = now.astimezone(ET)
    # Weekends
    if now.weekday() >= 5:
        return MarketPhase.CLOSED
    return _phase(now.time(), US_PRE_SCAN_START, US_OPEN, US_CLOSE)


def is_any_market_active(now: datetime | None = None) -> bool:
    """Return True if either KR or US market is in pre-scan or open phase."""
    kr = get_kr_phase(now)
    us = get_us_phase(now)
    return kr != MarketPhase.CLOSED or us != MarketPhase.CLOSED


def get_market_status(now: datetime | None = None) -> dict:
    """Return a dict describing both markets' current status (for the API)."""
    if now is None:
        now = datetime.now(KST)

    kr_phase = get_kr_phase(now)
    us_phase = get_us_phase(now)

    now_kst = now.astimezone(KST)
    now_et = now.astimezone(ET)

    return {
        "kr": {
            "phase": kr_phase.value,
            "local_time": now_kst.strftime("%H:%M:%S"),
            "timezone": "KST",
            "hours": "08:30-15:30",
        },
        "us": {
            "phase": us_phase.value,
            "local_time": now_et.strftime("%H:%M:%S"),
            "timezone": "ET",
            "hours": "09:00-16:00",
        },
        "any_active": is_any_market_active(now),
    }
