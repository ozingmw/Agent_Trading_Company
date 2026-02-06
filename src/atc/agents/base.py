from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional

from atc.audit import AuditLog
from atc.config import AppConfig, Secrets
from atc.events import Event, EventBus, EventRecorder
from atc.guidelines import GuidelineManager
from atc.memory import MemoryManager
from atc.session_manager import SessionManager
from atc.types import AgentStatus


@dataclass
class AgentContext:
    config: AppConfig
    secrets: Secrets
    bus: EventBus
    audit: AuditLog
    guideline_manager: GuidelineManager
    memory_manager: MemoryManager
    session_manager: SessionManager
    event_recorder: EventRecorder
    data_collector: object
    broker: object
    universe_manager: object


class AgentRegistry:
    def __init__(self) -> None:
        self._statuses: Dict[str, AgentStatus] = {}

    def set_status(self, name: str, state: str, last_action: Optional[str] = None, last_error: Optional[str] = None) -> None:
        self._statuses[name] = AgentStatus(
            name=name,
            state=state,
            last_action=last_action,
            last_error=last_error,
            updated_at=datetime.utcnow(),
        )

    def get_statuses(self) -> Dict[str, AgentStatus]:
        return dict(self._statuses)


class BaseAgent:
    def __init__(self, name: str, context: AgentContext, registry: AgentRegistry) -> None:
        self.name = name
        self.context = context
        self.registry = registry
        self.logger = logging.getLogger(name)
        self.registry.set_status(name, "initialized")
        self.context.memory_manager.init_agent_memory(name)
        self.global_guidelines = self.context.guideline_manager.load_global()
        self.agent_guidelines = self.context.guideline_manager.load_agent(name)
        self.logger.info("onboarded")

    async def emit(self, event_type: str, payload: dict, cycle_id: Optional[str] = None) -> None:
        event = Event(type=event_type, payload=payload, source=self.name, cycle_id=cycle_id)
        await self.context.bus.publish(event)
        self.context.audit.log_event(self.name, event_type, payload, cycle_id=cycle_id)

    def update_status(self, state: str, last_action: Optional[str] = None, last_error: Optional[str] = None) -> None:
        self.registry.set_status(self.name, state, last_action=last_action, last_error=last_error)

    def reload_guidelines(self) -> None:
        self.global_guidelines = self.context.guideline_manager.load_global()
        self.agent_guidelines = self.context.guideline_manager.load_agent(self.name)
