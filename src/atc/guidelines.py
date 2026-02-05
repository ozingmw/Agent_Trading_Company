from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Iterable, List

from atc.types import GuidelineProposal


class GuidelineManager:
    def __init__(self, global_path: str | Path, agent_dir: str | Path) -> None:
        self.global_path = Path(global_path)
        self.agent_dir = Path(agent_dir)
        self.agent_dir.mkdir(parents=True, exist_ok=True)

    def load_global(self) -> str:
        return self.global_path.read_text(encoding="utf-8")

    def load_agent(self, agent_name: str) -> str:
        path = self.agent_dir / f"{agent_name}.md"
        if not path.exists():
            path.write_text(f"# {agent_name} Guidelines\n", encoding="utf-8")
        return path.read_text(encoding="utf-8")

    def apply_proposal(self, proposal: GuidelineProposal) -> Path:
        target_path = (
            self.global_path
            if proposal.target == "global"
            else self.agent_dir / f"{proposal.target}.md"
        )
        timestamp = proposal.created_at.isoformat(timespec="seconds") + "Z"
        entry = (
            f"\n## {proposal.title}\n"
            f"- Proposed by: {proposal.proposer}\n"
            f"- Approved at: {timestamp}\n"
            f"\n{proposal.content}\n"
        )
        existing = target_path.read_text(encoding="utf-8") if target_path.exists() else ""
        target_path.write_text(existing + entry, encoding="utf-8")
        return target_path

    def scan_proposals(self, proposals_dir: str | Path) -> List[GuidelineProposal]:
        proposals_path = Path(proposals_dir)
        proposals_path.mkdir(parents=True, exist_ok=True)
        proposals: List[GuidelineProposal] = []
        for file_path in proposals_path.glob("*.json"):
            data = json.loads(file_path.read_text(encoding="utf-8"))
            proposals.append(GuidelineProposal.model_validate(data))
            file_path.unlink(missing_ok=True)
        return proposals
