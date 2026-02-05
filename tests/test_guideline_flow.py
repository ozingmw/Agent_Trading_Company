import json
from pathlib import Path

from atc.guidelines import GuidelineManager
from atc.types import GuidelineProposal


def test_guideline_proposal_apply(tmp_path: Path) -> None:
    global_doc = tmp_path / "agent_guidelines.md"
    agent_dir = tmp_path / "agents"
    proposals_dir = tmp_path / "agents" / "proposals"
    agent_dir.mkdir(parents=True, exist_ok=True)
    proposals_dir.mkdir(parents=True, exist_ok=True)
    global_doc.write_text("# Agent Guidelines\n", encoding="utf-8")

    proposal_data = {
        "target": "global",
        "title": "Test Update",
        "content": "Add a new rule.",
        "proposer": "TestAgent",
    }
    proposal_file = proposals_dir / "proposal.json"
    proposal_file.write_text(json.dumps(proposal_data), encoding="utf-8")

    manager = GuidelineManager(global_doc, agent_dir)
    proposals = manager.scan_proposals(proposals_dir)
    assert len(proposals) == 1

    manager.apply_proposal(proposals[0])
    updated = global_doc.read_text(encoding="utf-8")
    assert "Test Update" in updated
