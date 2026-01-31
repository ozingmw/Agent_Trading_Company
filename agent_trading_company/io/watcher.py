from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


ReadyHandler = Callable[[Path], None]


def _normalize_path(raw_path: object) -> str:
    if isinstance(raw_path, bytes):
        return raw_path.decode()
    if isinstance(raw_path, str):
        return raw_path
    return str(raw_path)


def _is_ready_path(path: Path) -> bool:
    return path.suffix == ".md" and not path.name.endswith(".md.tmp")


@dataclass
class ArtifactReadyHandler(FileSystemEventHandler):
    on_ready: ReadyHandler

    def on_created(self, event: Any) -> None:
        if event.is_directory:
            return
        src_path = _normalize_path(event.src_path)
        path = Path(src_path)  # type: ignore[arg-type,reportArgumentType]
        if _is_ready_path(path):
            self.on_ready(path)

    def on_moved(self, event: Any) -> None:
        if event.is_directory:
            return
        dest_path_value = _normalize_path(event.dest_path)
        dest_path = Path(dest_path_value)  # type: ignore[arg-type,reportArgumentType]
        if _is_ready_path(dest_path):
            self.on_ready(dest_path)


def start_watcher(paths: list[Path], handler: FileSystemEventHandler) -> Observer:
    observer = Observer()
    for watch_path in paths:
        watch_path.mkdir(parents=True, exist_ok=True)
        observer.schedule(handler, str(watch_path), recursive=True)
    observer.start()
    return observer
