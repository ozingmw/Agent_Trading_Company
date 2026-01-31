from __future__ import annotations

from pathlib import Path

from agent_trading_company.io.atomic_writer import atomic_write
from agent_trading_company.io.watcher import ArtifactReadyHandler


def test_atomic_write_creates_ready_file(tmp_path: Path) -> None:
    target = tmp_path / "artifacts" / "collector" / "sample.md"
    atomic_write(target, "hello")

    assert target.exists()
    assert not target.with_suffix(".md.tmp").exists()


def test_watcher_handler_ignores_tmp_and_emits_ready(tmp_path: Path) -> None:
    ready_paths: list[Path] = []

    handler = ArtifactReadyHandler(on_ready=ready_paths.append)

    tmp_path_md = tmp_path / "artifacts" / "status.md.tmp"
    tmp_path_md.parent.mkdir(parents=True, exist_ok=True)

    class CreatedEvent:
        def __init__(self, src_path: str) -> None:
            self.src_path = src_path
            self.is_directory = False

    class MovedEvent:
        def __init__(self, src_path: str, dest_path: str) -> None:
            self.src_path = src_path
            self.dest_path = dest_path
            self.is_directory = False

    handler.on_created(CreatedEvent(str(tmp_path_md)))
    assert ready_paths == []

    final_path = tmp_path / "artifacts" / "collector" / "ready.md"
    handler.on_moved(MovedEvent(str(tmp_path_md), str(final_path)))
    assert ready_paths == [final_path]
