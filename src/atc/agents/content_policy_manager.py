from __future__ import annotations

import asyncio

from atc.agents.base import AgentContext, AgentRegistry, BaseAgent
from atc.types import GuidelineProposal


class ContentPolicyManagerAgent(BaseAgent):
    def __init__(self, name: str, context: AgentContext, registry: AgentRegistry) -> None:
        super().__init__(name, context, registry)
        self.proposals_dir = "docs/agents/proposals"

    async def _handle_proposal(self, proposal: GuidelineProposal) -> None:
        self.context.guideline_manager.apply_proposal(proposal)
        await self.emit(
            "GuidelineUpdated",
            {"target": proposal.target, "title": proposal.title},
            cycle_id=None,
        )

    async def run(self) -> None:
        queue = await self.context.bus.subscribe("GuidelineProposal")
        while True:
            proposals = []
            try:
                event = await asyncio.wait_for(queue.get(), timeout=30)
                proposals.append(GuidelineProposal.model_validate(event.payload))
            except asyncio.TimeoutError:
                pass

            proposals.extend(self.context.guideline_manager.scan_proposals(self.proposals_dir))
            for proposal in proposals:
                self.update_status("running", last_action=f"proposal {proposal.title}")
                await self._handle_proposal(proposal)
            if proposals:
                self.update_status("idle", last_action=f"applied {len(proposals)} proposals")
