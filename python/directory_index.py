from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import threading
from typing import Callable


DEFAULT_EXCLUDES = frozenset(
    {
        ".git",
        "node_modules",
        ".venv",
        "venv",
        "__pycache__",
        "dist",
        "build",
        ".idea",
        ".vscode",
    }
)


@dataclass(frozen=True)
class DirectoryEntry:
    name: str
    path: str
    normalized_path: str
    root_path: str
    relative_path: str


class DirectoryIndex:
    """Thread-safe recursive directory index with immutable snapshots."""

    def __init__(self, roots: list[str], excludes=DEFAULT_EXCLUDES, logger=None):
        self.roots = self._deduplicate_roots(roots)
        self.excludes = frozenset(str(item).casefold() for item in excludes)
        self.logger = logger
        self._snapshot: tuple[DirectoryEntry, ...] = ()
        self._failures: tuple[str, ...] = ()
        self._lock = threading.RLock()
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    @staticmethod
    def _normalize(path: str) -> str:
        return os.path.normpath(path or "").replace("\\", "/").casefold()

    @classmethod
    def _is_descendant(cls, candidate: str, parent: str) -> bool:
        candidate_key = cls._normalize(candidate)
        parent_key = cls._normalize(parent).rstrip("/")
        return candidate_key == parent_key or candidate_key.startswith(parent_key + "/")

    @classmethod
    def _deduplicate_roots(cls, roots: list[str]) -> tuple[str, ...]:
        ordered: list[str] = []
        for raw in roots:
            value = str(raw)
            if not os.path.isdir(value):
                continue
            if any(cls._is_descendant(value, existing) for existing in ordered):
                continue
            ordered = [
                existing for existing in ordered
                if not cls._is_descendant(existing, value)
            ]
            ordered.append(value)
        return tuple(ordered)

    @property
    def snapshot(self) -> tuple[DirectoryEntry, ...]:
        with self._lock:
            return self._snapshot

    @property
    def failures(self) -> tuple[str, ...]:
        with self._lock:
            return self._failures

    @property
    def refreshing(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def scan_now(self) -> tuple[tuple[DirectoryEntry, ...], tuple[str, ...]]:
        entries: dict[str, DirectoryEntry] = {}
        failures: list[str] = []

        for root in self.roots:
            if self._stop_event.is_set():
                break
            root_path = Path(root)
            root_normalized = self._normalize(str(root_path))
            entries[root_normalized] = DirectoryEntry(
                name=root_path.name or str(root_path),
                path=str(root_path),
                normalized_path=root_normalized,
                root_path=str(root_path),
                relative_path=".",
            )

            def onerror(error: OSError) -> None:
                filename = str(getattr(error, "filename", "") or root_path)
                if filename not in failures:
                    failures.append(filename)

            try:
                for current, dirnames, _filenames in os.walk(
                    root_path,
                    topdown=True,
                    onerror=onerror,
                    followlinks=False,
                ):
                    if self._stop_event.is_set():
                        break
                    dirnames[:] = sorted(
                        name
                        for name in dirnames
                        if name.casefold() not in self.excludes
                    )
                    for name in dirnames:
                        path = Path(current) / name
                        normalized = self._normalize(str(path))
                        if normalized in entries:
                            continue
                        try:
                            relative = str(path.relative_to(root_path))
                        except ValueError:
                            relative = name
                        entries[normalized] = DirectoryEntry(
                            name=name,
                            path=str(path),
                            normalized_path=normalized,
                            root_path=str(root_path),
                            relative_path=relative,
                        )
            except (OSError, PermissionError) as exc:
                failed = str(getattr(exc, "filename", "") or root_path)
                if failed not in failures:
                    failures.append(failed)

        snapshot = tuple(sorted(entries.values(), key=lambda item: item.normalized_path))
        failure_tuple = tuple(failures)
        with self._lock:
            self._snapshot = snapshot
            self._failures = failure_tuple
        if self.logger:
            self.logger.info(
                "directory index completed entries=%s failures=%s",
                len(snapshot),
                len(failure_tuple),
            )
        return snapshot, failure_tuple

    def refresh_async(
        self,
        scheduler: Callable[[Callable[[], None]], object],
        on_complete: Callable[[tuple[DirectoryEntry, ...], tuple[str, ...]], None],
    ) -> bool:
        if self.refreshing:
            return False
        self._stop_event.clear()

        def worker() -> None:
            snapshot, failures = self.scan_now()
            if self._stop_event.is_set():
                return
            try:
                scheduler(lambda: on_complete(snapshot, failures))
            except Exception as exc:
                if self.logger:
                    self.logger.warning("directory index callback scheduling failed: %s", exc)

        self._thread = threading.Thread(
            target=worker,
            daemon=True,
            name="launcher-directory-index",
        )
        self._thread.start()
        return True

    def wait(self, timeout: float | None = None) -> None:
        thread = self._thread
        if thread:
            thread.join(timeout)

    def stop(self) -> None:
        self._stop_event.set()
        self.wait(timeout=1.0)

    def search(
        self,
        query: str,
        recent_timestamps: dict[str, float] | None = None,
        limit: int = 30,
    ) -> list[DirectoryEntry]:
        needle = query.strip().casefold()
        if not needle or limit <= 0:
            return []
        recent = {
            self._normalize(path): float(stamp)
            for path, stamp in (recent_timestamps or {}).items()
        }

        ranked: list[tuple[tuple[object, ...], DirectoryEntry]] = []
        for entry in self.snapshot:
            name = entry.name.casefold()
            relative = entry.relative_path.casefold()
            if name == needle:
                rank = 0
            elif name.startswith(needle):
                rank = 1
            elif needle in name:
                rank = 2
            elif needle in relative:
                rank = 3
            else:
                continue
            score = (
                rank,
                -recent.get(entry.normalized_path, 0.0),
                name,
                entry.normalized_path,
            )
            ranked.append((score, entry))

        ranked.sort(key=lambda item: item[0])
        return [entry for _score, entry in ranked[:limit]]
