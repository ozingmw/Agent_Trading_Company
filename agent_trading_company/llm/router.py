from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from openai import OpenAI


class LLMProvider(Protocol):
    def complete(self, system: str, user: str) -> str:
        ...


@dataclass
class OpenAIProvider:
    model: str = "gpt-4.1-mini"

    def __post_init__(self) -> None:
        self._client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def complete(self, system: str, user: str) -> str:
        response = self._client.responses.create(
            model=self.model,
            input=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        )
        return response.output_text


@dataclass
class LLMRouter:
    skills_root: Path
    provider: LLMProvider

    def _skill_path(self, name: str) -> Path:
        return self.skills_root / name / "SKILL.md"

    def load_skill(self, name: str) -> str:
        path = self._skill_path(name)
        if not path.exists():
            raise FileNotFoundError(f"Missing skill: {name}")
        return path.read_text(encoding="utf-8")

    def invoke(self, name: str, payload: dict[str, Any]) -> dict[str, Any]:
        skill_text = self.load_skill(name)
        system = (
            "You are a decision engine. Follow the SKILL instructions exactly. "
            "Return ONLY valid JSON with double quotes and no extra text."
        )
        user = f"SKILL:\n{skill_text}\n\nINPUT:\n{json.dumps(payload, ensure_ascii=False)}"
        raw = self.provider.complete(system=system, user=user)
        return _parse_json(raw)


def _parse_json(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


_router: LLMRouter | None = None


def get_router() -> LLMRouter:
    global _router
    if _router is None:
        provider_name = os.getenv("LLM_PROVIDER", "openai").lower()
        if provider_name == "openai":
            provider = OpenAIProvider()
        else:
            raise NotImplementedError("Only openai provider is configured in MVP")
        _router = LLMRouter(skills_root=Path("skills"), provider=provider)
    return _router


def set_router(router: LLMRouter) -> None:
    global _router
    _router = router
