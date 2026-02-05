from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass(slots=True)
class Event:
    type: str
    payload: Dict[str, Any]
    source: str
    ts: datetime = field(default_factory=datetime.utcnow)
    cycle_id: Optional[str] = None


class EventRecorder:
    def __init__(self) -> None:
        self._events: Dict[str, List[Event]] = {}
        self._lock = asyncio.Lock()

    async def record(self, event: Event) -> None:
        if event.cycle_id is None:
            return
        async with self._lock:
            self._events.setdefault(event.cycle_id, []).append(event)

    async def get_cycle_events(self, cycle_id: str) -> List[Event]:
        async with self._lock:
            return list(self._events.get(cycle_id, []))


class EventBus:
    def __init__(self, recorder: Optional[EventRecorder] = None) -> None:
        self._subscribers: Dict[str, List[asyncio.Queue[Event]]] = {}
        self._lock = asyncio.Lock()
        self._recorder = recorder

    async def publish(self, event: Event) -> None:
        if self._recorder:
            await self._recorder.record(event)
        async with self._lock:
            queues = list(self._subscribers.get(event.type, [])) + list(
                self._subscribers.get("*", [])
            )
        for queue in queues:
            await queue.put(event)

    async def subscribe(self, event_type: str) -> asyncio.Queue[Event]:
        queue: asyncio.Queue[Event] = asyncio.Queue()
        async with self._lock:
            self._subscribers.setdefault(event_type, []).append(queue)
        return queue

    async def wait_for(self, event_type: str, cycle_id: str, timeout: float) -> Event:
        queue = await self.subscribe(event_type)
        try:
            while True:
                event = await asyncio.wait_for(queue.get(), timeout=timeout)
                if event.cycle_id == cycle_id:
                    return event
        finally:
            await self._unsubscribe(event_type, queue)

    async def _unsubscribe(self, event_type: str, queue: asyncio.Queue[Event]) -> None:
        async with self._lock:
            queues = self._subscribers.get(event_type, [])
            if queue in queues:
                queues.remove(queue)
