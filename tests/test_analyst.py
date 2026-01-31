from __future__ import annotations

import json
from pathlib import Path

from agent_trading_company.agents import analyst
from agent_trading_company.core.directives import load_directives


def _write_collector_artifact(tmp_path: Path, data_path: Path) -> Path:
    artifact = tmp_path / "artifacts" / "collector" / "collector.md"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    content = (
        "---\n"
        "artifact_id: \"c1\"\n"
        "agent_id: \"collector-1\"\n"
        "role: \"collector\"\n"
        "created_at: \"2026-01-30T00:00:00Z\"\n"
        "inputs: []\n"
        f"outputs: [\"{data_path}\"]\n"
        "directive_hash: \"hash\"\n"
        "payload:\n"
        f"  outputs_by_source:\n    kis: \"{data_path}\"\n"
        "  sources: [kis]\n"
        "  universe: \"OVERSEAS\"\n"
        "  counts: {kis: 2}\n"
        "status: \"completed\"\n"
        "---\n"
    )
    artifact.write_text(content, encoding="utf-8")
    return artifact


def test_analyst_writes_signal(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    directives_dir = tmp_path / "directives"
    directives_dir.mkdir(parents=True, exist_ok=True)
    directives = directives_dir / "admin_directives.md"
    directives.write_text(
        "---\nmarket_universe: OVERSEAS\n"
        "default_order_size: 2\n"
        "---\n",
        encoding="utf-8",
    )
    directives_obj, _ = load_directives(directives)

    data_path = tmp_path / "data" / "raw" / "kis_quotes.jsonl"
    data_path.parent.mkdir(parents=True, exist_ok=True)
    data_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "ts": "2026-01-30T00:00:00Z",
                        "source": "kis",
                        "symbol": "AAPL",
                        "exchange": "NASD",
                        "price": 100,
                    }
                ),
                json.dumps(
                    {
                        "ts": "2026-01-30T00:01:00Z",
                        "source": "kis",
                        "symbol": "AAPL",
                        "exchange": "NASD",
                        "price": 101,
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    artifact = _write_collector_artifact(tmp_path, data_path)
    output = analyst.run(str(artifact), directives_obj.__dict__, object())
    output_path = Path(output)
    assert output_path.exists()
    content = output_path.read_text(encoding="utf-8")
    assert "role: analyst" in content
