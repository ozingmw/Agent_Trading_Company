from __future__ import annotations

import asyncio

from atc.agents import (
    AgentContext,
    AgentRegistry,
    ContentPolicyManagerAgent,
    CoordinatorAgent,
    CriticAgent,
    DataCollectionAgent,
    ExecutionAgent,
    MemorySummarizerAgent,
    OpsAgent,
    PortfolioAgent,
    SignalAgent,
    SelfReflectionAgent,
)


class AgentRunner:
    def __init__(self, context: AgentContext, registry: AgentRegistry) -> None:
        self.context = context
        self.registry = registry
        self.agents = [
            CoordinatorAgent("CoordinatorAgent", context, registry),
            DataCollectionAgent("DataCollectionAgent", context, registry),
            SignalAgent("SignalAgent", context, registry),
            PortfolioAgent("PortfolioAgent", context, registry),
            ExecutionAgent("ExecutionAgent", context, registry),
            OpsAgent("OpsAgent", context, registry),
            CriticAgent("CriticAgent", context, registry),
            MemorySummarizerAgent("MemorySummarizerAgent", context, registry),
            ContentPolicyManagerAgent("ContentPolicyManagerAgent", context, registry),
            SelfReflectionAgent("SelfReflectionAgent", context, registry),
        ]

    async def run(self) -> None:
        tasks = [asyncio.create_task(agent.run()) for agent in self.agents]
        for agent in self.agents:
            tasks.append(asyncio.create_task(self._watch_guidelines(agent)))
        await asyncio.gather(*tasks)

    async def _watch_guidelines(self, agent) -> None:
        queue = await self.context.bus.subscribe("GuidelineUpdated")
        while True:
            await queue.get()
            agent.reload_guidelines()
