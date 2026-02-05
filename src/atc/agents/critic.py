from __future__ import annotations

from atc.agents.base import AgentContext, AgentRegistry, BaseAgent
from atc.types import CriticFeedback, SignalBatch


class CriticAgent(BaseAgent):
    def _score_batch(self, batch: SignalBatch) -> tuple[float, str]:
        score = 0.4
        notes = []
        if batch.intents:
            score += 0.2
        if all(intent.rationale for intent in batch.intents):
            score += 0.2
        if all(intent.data_used for intent in batch.intents):
            score += 0.1
        if batch.intents and all(intent.action == "HOLD" for intent in batch.intents):
            score -= 0.1
        notes.append(f"intents={len(batch.intents)}")
        score = max(0.0, min(1.0, score))
        return score, "; ".join(notes)

    async def run(self) -> None:
        queue = await self.context.bus.subscribe("CycleCompleted")
        while True:
            event = await queue.get()
            cycle_id = event.cycle_id or ""
            self.update_status("running", last_action=f"critic {cycle_id}")
            events = await self.context.event_recorder.get_cycle_events(cycle_id)
            signal_events = [e for e in events if e.type == "SignalGenerated"]
            if signal_events:
                payload = signal_events[-1].payload
                batch = SignalBatch.model_validate({"intents": payload.get("intents", [])})
                score, notes = self._score_batch(batch)
            else:
                score, notes = 0.0, "no signal events"
            feedback = CriticFeedback(
                agent="SignalAgent",
                cycle_id=cycle_id,
                score=score,
                notes=notes,
            )
            self.context.audit.log_feedback(
                feedback.agent, feedback.cycle_id, feedback.score, feedback.notes
            )
            self.context.memory_manager.append_entry(
                feedback.agent, "Feedback", f"Critic score {score:.2f}: {feedback.notes}"
            )
            await self.emit(
                "AgentFeedback",
                feedback.model_dump(),
                cycle_id=cycle_id,
            )
            self.update_status("idle", last_action=f"critic {cycle_id} done")
