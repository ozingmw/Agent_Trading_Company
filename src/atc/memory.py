from __future__ import annotations

from datetime import datetime
from pathlib import Path


MEMORY_SECTIONS = [
    "Profile",
    "Recent Actions",
    "Feedback",
    "Lessons",
    "Next Adjustments",
]


class MemoryManager:
    def __init__(self, memory_dir: str | Path) -> None:
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)

    def init_agent_memory(self, agent_name: str) -> Path:
        path = self.memory_dir / f"{agent_name}.md"
        if not path.exists():
            content = [f"# Agent Memory: {agent_name}"]
            for section in MEMORY_SECTIONS:
                content.append(f"\n## {section}\n")
            path.write_text("\n".join(content), encoding="utf-8")
        return path

    def append_entry(self, agent_name: str, section: str, entry: str) -> None:
        path = self.init_agent_memory(agent_name)
        timestamp = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        entry_block = f"- {timestamp} {entry}\n"
        text = path.read_text(encoding="utf-8")
        marker = f"## {section}"
        if marker not in text:
            text += f"\n{marker}\n"
        parts = text.split(marker)
        head = parts[0] + marker
        tail = marker.join(parts[1:])
        updated = head + "\n" + entry_block + tail
        path.write_text(updated, encoding="utf-8")

    def latest_entry(self, agent_name: str, section: str) -> str | None:
        path = self.init_agent_memory(agent_name)
        text = path.read_text(encoding="utf-8")
        marker = f"## {section}"
        if marker not in text:
            return None
        section_text = text.split(marker, 1)[1]
        lines = [
            line.strip()
            for line in section_text.splitlines()
            if line.strip().startswith("-")
        ]
        return lines[0] if lines else None
