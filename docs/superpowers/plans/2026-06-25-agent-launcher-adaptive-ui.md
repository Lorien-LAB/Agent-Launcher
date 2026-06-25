# Agent Launcher Adaptive UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the monolithic Agent Launcher window with a modular compact/expanded launcher that supports favorites, recent directories, background indexing, launch options, animated resizing, Terminal appearance preview/apply/rollback, and diagnostic logging without breaking Session Monitor or exact Terminal HWND routing.

**Architecture:** Keep `terminal_manager_core.py` as the composition and lifecycle root. Move Launcher state, indexing, animation, appearance transactions, launch orchestration, logging, and Tk rendering into focused modules. Preserve the existing Session Monitor override stack and exact-window behavior in `terminal_focus.py`, extending only the terminal-launch API needed by the new controller.

**Tech Stack:** Python 3.13, tkinter/ttk, pathlib/os, dataclasses, threading, logging.handlers.RotatingFileHandler, unittest, ctypes/Windows Terminal CLI.

---

## File map

### New runtime files

- `python/launcher_logging.py` — rotating diagnostic logger configuration.
- `python/launcher_state.py` — typed Launcher state, validation, migration, atomic persistence.
- `python/directory_index.py` — background directory scanning, immutable snapshots, ranked search.
- `python/launcher_animation.py` — 220 ms top-left-anchored window resize animation.
- `python/terminal_appearance.py` — preview/apply/cancel transaction around Windows Terminal appearance.
- `python/launch_controller.py` — Claude/Hermes launch validation, option mapping, recent-directory updates.
- `python/launcher_view.py` — compact/expanded Tk UI and event emission.

### Modified runtime files

- `python/terminal_focus.py` — extend launch API to accept window/tab mode and caller-supplied arguments while preserving exact HWND capture for new windows.
- `python/terminal_manager_core.py` — remove old Launcher UI/business methods and compose the new modules.
- `python/terminal_manager.py` — update entry-point documentation and preserve override ordering.
- `python/DEVELOPMENT.md` — document the new module graph and verification commands.

### New tests

- `python/tests/test_launcher_logging.py`
- `python/tests/test_launcher_state.py`
- `python/tests/test_directory_index.py`
- `python/tests/test_launcher_animation.py`
- `python/tests/test_terminal_appearance.py`
- `python/tests/test_launch_controller.py`
- `python/tests/test_launcher_view.py`
- `python/tests/test_launcher_integration.py`

### Existing tests retained

- `python/tests/test_session_panel_helpers.py`

## Execution prerequisites

Before Task 1, create an isolated worktree from `feat/session-monitor-panel-redesign` and confirm the branch contains design commit `fd8c45a305fe753a634c28b484de6b7a41672e53`.

Run:

```bash
git fetch origin
git worktree add ../agent-launcher-adaptive-ui -b feat/agent-launcher-adaptive-ui origin/feat/session-monitor-panel-redesign
cd ../agent-launcher-adaptive-ui
git log -1 --oneline
```

Expected: the latest history includes `docs: specify adaptive Agent Launcher redesign`.

---

### Task 1: Add rotating diagnostic logging

**Files:**
- Create: `python/launcher_logging.py`
- Create: `python/tests/test_launcher_logging.py`

- [ ] **Step 1: Write the failing logging tests**

Create `python/tests/test_launcher_logging.py`:

```python
import logging
import pathlib
import tempfile
import unittest

from launcher_logging import configure_launcher_logger


class LauncherLoggingTests(unittest.TestCase):
    def test_logger_creates_rotating_file_handler(self):
        with tempfile.TemporaryDirectory() as tmp:
            logger = configure_launcher_logger(pathlib.Path(tmp) / "agent-launcher.log")
            logger.info("indexed %s directories", 12)
            for handler in logger.handlers:
                handler.flush()

            log_path = pathlib.Path(tmp) / "agent-launcher.log"
            self.assertTrue(log_path.exists())
            self.assertIn("indexed 12 directories", log_path.read_text(encoding="utf-8"))

    def test_reconfiguration_does_not_duplicate_handlers(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "agent-launcher.log"
            first = configure_launcher_logger(path)
            second = configure_launcher_logger(path)
            self.assertIs(first, second)
            self.assertEqual(len(second.handlers), 1)
            self.assertIsInstance(second.handlers[0], logging.Handler)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test and verify failure**

Run:

```bash
python -m unittest python.tests.test_launcher_logging -v
```

Expected: `ModuleNotFoundError: No module named 'launcher_logging'`.

- [ ] **Step 3: Implement the rotating logger**

Create `python/launcher_logging.py`:

```python
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


LOGGER_NAME = "agent_launcher"


def configure_launcher_logger(log_path: str | Path) -> logging.Logger:
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    resolved = str(path.resolve())
    existing = [
        handler
        for handler in logger.handlers
        if isinstance(handler, RotatingFileHandler)
        and str(Path(handler.baseFilename).resolve()) == resolved
    ]
    if existing:
        logger.handlers[:] = [existing[0]]
        return logger

    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()

    handler = RotatingFileHandler(
        path,
        maxBytes=1_048_576,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    logger.addHandler(handler)
    return logger
```

- [ ] **Step 4: Run the logging tests**

Run:

```bash
python -m unittest python.tests.test_launcher_logging -v
```

Expected: 2 tests pass.

- [ ] **Step 5: Commit**

```bash
git add python/launcher_logging.py python/tests/test_launcher_logging.py
git commit -m "feat: add launcher diagnostic logging"
```

---

### Task 2: Implement typed Launcher state and atomic persistence

**Files:**
- Create: `python/launcher_state.py`
- Create: `python/tests/test_launcher_state.py`

- [ ] **Step 1: Write failing tests for defaults, favorites, recents, corruption, and atomic save**

Create `python/tests/test_launcher_state.py`:

```python
import json
import pathlib
import tempfile
import unittest

from launcher_state import (
    AppearanceSettings,
    LaunchOptions,
    LauncherStateStore,
)


class LauncherStateStoreTests(unittest.TestCase):
    def test_defaults_are_compact_window_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = LauncherStateStore(pathlib.Path(tmp) / "launcher-state.json")
            state = store.load()
            self.assertEqual(state.window_x, 120)
            self.assertEqual(state.window_y, 80)
            self.assertEqual(state.favorites, [])
            self.assertEqual(state.recent_directories, [])
            self.assertEqual(state.launch_options, LaunchOptions())
            self.assertEqual(state.appearance, AppearanceSettings())

    def test_favorites_are_normalized_and_deduplicated(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            project = root / "Project"
            project.mkdir()
            store = LauncherStateStore(root / "launcher-state.json")
            store.load()
            store.toggle_favorite(str(project))
            store.toggle_favorite(str(project).upper())
            self.assertEqual(store.state.favorites, [])
            store.toggle_favorite(str(project))
            self.assertEqual(len(store.state.favorites), 1)

    def test_recent_directories_are_deduplicated_and_limited_to_eight(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            store = LauncherStateStore(root / "launcher-state.json")
            store.load()
            projects = []
            for index in range(10):
                project = root / f"p{index}"
                project.mkdir()
                projects.append(project)
                store.record_recent(str(project))
            store.record_recent(str(projects[5]))
            self.assertEqual(len(store.state.recent_directories), 8)
            self.assertEqual(store.state.recent_directories[0], str(projects[5]))

    def test_corrupt_file_is_backed_up_and_defaults_are_returned(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            path = root / "launcher-state.json"
            path.write_text("{not-json", encoding="utf-8")
            store = LauncherStateStore(path)
            state = store.load()
            self.assertEqual(state.favorites, [])
            backups = list(root.glob("launcher-state.corrupt-*.json"))
            self.assertEqual(len(backups), 1)

    def test_save_writes_valid_json_without_leaving_tmp_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            path = root / "launcher-state.json"
            store = LauncherStateStore(path)
            store.load()
            store.update_window_position(42, 84)
            store.update_launch_options(
                LaunchOptions(
                    terminal_mode="tab",
                    skip_permissions=True,
                    hide_after_launch=True,
                )
            )
            store.save()
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["window"], {"x": 42, "y": 84})
            self.assertEqual(payload["launch_options"]["terminal_mode"], "tab")
            self.assertFalse(path.with_suffix(".json.tmp").exists())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the state tests and verify failure**

Run:

```bash
python -m unittest python.tests.test_launcher_state -v
```

Expected: `ModuleNotFoundError: No module named 'launcher_state'`.

- [ ] **Step 3: Implement state types and store**

Create `python/launcher_state.py` with these public types and methods:

```python
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
import json
import os
from pathlib import Path


STATE_VERSION = 1
DEFAULT_STATE_PATH = Path.home() / ".agent-launcher" / "launcher-state.json"


@dataclass(frozen=True)
class LaunchOptions:
    terminal_mode: str = "window"
    skip_permissions: bool = False
    hide_after_launch: bool = False

    def __post_init__(self) -> None:
        if self.terminal_mode not in {"window", "tab"}:
            raise ValueError("terminal_mode must be 'window' or 'tab'")


@dataclass(frozen=True)
class AppearanceSettings:
    mode: str = "none"
    opacity: int = 50

    def __post_init__(self) -> None:
        if self.mode not in {"acrylic", "opacity", "none"}:
            raise ValueError("unsupported appearance mode")
        if not 0 <= int(self.opacity) <= 100:
            raise ValueError("opacity must be between 0 and 100")


@dataclass
class LauncherState:
    version: int = STATE_VERSION
    window_x: int = 120
    window_y: int = 80
    favorites: list[str] = field(default_factory=list)
    recent_directories: list[str] = field(default_factory=list)
    launch_options: LaunchOptions = field(default_factory=LaunchOptions)
    appearance: AppearanceSettings = field(default_factory=AppearanceSettings)


def normalize_path(path: str) -> str:
    return os.path.normcase(os.path.normpath(path))


def _deduplicate_existing(paths: list[str], limit: int | None = None) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for raw in paths:
        normalized = normalize_path(str(raw))
        if normalized in seen:
            continue
        if not os.path.isdir(raw):
            continue
        seen.add(normalized)
        output.append(str(raw))
        if limit is not None and len(output) >= limit:
            break
    return output


class LauncherStateStore:
    def __init__(self, path: str | Path = DEFAULT_STATE_PATH, logger=None):
        self.path = Path(path)
        self.logger = logger
        self.state = LauncherState()
        self.recovered_corrupt_file = False

    def load(self) -> LauncherState:
        self.recovered_corrupt_file = False
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            self.state = self._from_payload(payload)
        except FileNotFoundError:
            self.state = LauncherState()
        except (json.JSONDecodeError, OSError, TypeError, ValueError):
            self._backup_corrupt_file()
            self.state = LauncherState()
            self.recovered_corrupt_file = True
        return self.state

    def _from_payload(self, payload: dict) -> LauncherState:
        if int(payload.get("version", 0)) != STATE_VERSION:
            raise ValueError("unsupported state version")
        window = payload.get("window", {})
        options = LaunchOptions(**payload.get("launch_options", {}))
        appearance = AppearanceSettings(**payload.get("appearance", {}))
        return LauncherState(
            version=STATE_VERSION,
            window_x=int(window.get("x", 120)),
            window_y=int(window.get("y", 80)),
            favorites=_deduplicate_existing(list(payload.get("favorites", []))),
            recent_directories=_deduplicate_existing(
                list(payload.get("recent_directories", [])), limit=8
            ),
            launch_options=options,
            appearance=appearance,
        )

    def _backup_corrupt_file(self) -> None:
        if not self.path.exists():
            return
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = self.path.with_name(f"launcher-state.corrupt-{stamp}.json")
        self.path.replace(backup)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        payload = {
            "version": STATE_VERSION,
            "window": {"x": self.state.window_x, "y": self.state.window_y},
            "favorites": self.state.favorites,
            "recent_directories": self.state.recent_directories,
            "launch_options": asdict(self.state.launch_options),
            "appearance": asdict(self.state.appearance),
        }
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(temporary, self.path)

    def toggle_favorite(self, path: str) -> bool:
        normalized = normalize_path(path)
        matches = [normalize_path(item) == normalized for item in self.state.favorites]
        if any(matches):
            self.state.favorites = [
                item for item in self.state.favorites
                if normalize_path(item) != normalized
            ]
            self.save()
            return False
        if not os.path.isdir(path):
            raise FileNotFoundError(path)
        self.state.favorites.append(path)
        self.save()
        return True

    def record_recent(self, path: str) -> None:
        if not os.path.isdir(path):
            raise FileNotFoundError(path)
        normalized = normalize_path(path)
        remaining = [
            item for item in self.state.recent_directories
            if normalize_path(item) != normalized
        ]
        self.state.recent_directories = [path, *remaining][:8]
        self.save()

    def update_window_position(self, x: int, y: int) -> None:
        self.state.window_x = int(x)
        self.state.window_y = int(y)

    def update_launch_options(self, options: LaunchOptions) -> None:
        self.state.launch_options = options
        self.save()

    def update_appearance(self, settings: AppearanceSettings) -> None:
        self.state.appearance = settings
        self.save()
```

- [ ] **Step 4: Run the state tests**

Run:

```bash
python -m unittest python.tests.test_launcher_state -v
```

Expected: 5 tests pass.

- [ ] **Step 5: Commit**

```bash
git add python/launcher_state.py python/tests/test_launcher_state.py
git commit -m "feat: add persistent launcher state"
```

---

### Task 3: Build background directory indexing and ranked search

**Files:**
- Create: `python/directory_index.py`
- Create: `python/tests/test_directory_index.py`

- [ ] **Step 1: Write failing directory-index tests**

Create `python/tests/test_directory_index.py`:

```python
import pathlib
import tempfile
import threading
import unittest

from directory_index import DirectoryIndex


class DirectoryIndexTests(unittest.TestCase):
    def test_scan_recurses_and_excludes_heavy_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "Alpha" / "Nested").mkdir(parents=True)
            (root / "node_modules" / "Hidden").mkdir(parents=True)
            index = DirectoryIndex([str(root)])
            snapshot, failures = index.scan_now()
            paths = {entry.path for entry in snapshot}
            self.assertIn(str(root / "Alpha"), paths)
            self.assertIn(str(root / "Alpha" / "Nested"), paths)
            self.assertNotIn(str(root / "node_modules"), paths)
            self.assertEqual(failures, ())

    def test_overlapping_roots_do_not_duplicate_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            child = root / "Project"
            nested = child / "src"
            nested.mkdir(parents=True)
            index = DirectoryIndex([str(root), str(child)])
            snapshot, _failures = index.scan_now()
            normalized = [entry.normalized_path for entry in snapshot]
            self.assertEqual(len(normalized), len(set(normalized)))

    def test_search_ranks_exact_prefix_contains_then_relative_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            for relative in (
                "alpha",
                "alphabet",
                "my-alpha-project",
                "group/other",
                "alpha-parent/child",
            ):
                (root / relative).mkdir(parents=True)
            index = DirectoryIndex([str(root)])
            index.scan_now()
            recent = {str(root / "alphabet"): 10.0}
            results = index.search("alpha", recent)
            self.assertEqual(results[0].name, "alpha")
            self.assertEqual(results[1].name, "alphabet")
            self.assertEqual(results[2].name, "alpha-parent")
            self.assertEqual(results[3].name, "my-alpha-project")

    def test_async_refresh_marshals_completion_through_scheduler(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "Project").mkdir()
            scheduled = []
            completed = threading.Event()

            def scheduler(callback):
                scheduled.append(callback)

            index = DirectoryIndex([str(root)])
            index.refresh_async(
                scheduler=scheduler,
                on_complete=lambda snapshot, failures: completed.set(),
            )
            index.wait(timeout=2.0)
            self.assertEqual(len(scheduled), 1)
            self.assertFalse(completed.is_set())
            scheduled[0]()
            self.assertTrue(completed.is_set())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the index tests and verify failure**

Run:

```bash
python -m unittest python.tests.test_directory_index -v
```

Expected: `ModuleNotFoundError: No module named 'directory_index'`.

- [ ] **Step 3: Implement indexing, immutable snapshots, refresh, and search**

Create `python/directory_index.py`:

```python
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
    def __init__(self, roots: list[str], excludes=DEFAULT_EXCLUDES, logger=None):
        self.roots = self._deduplicate_roots(roots)
        self.excludes = frozenset(item.casefold() for item in excludes)
        self.logger = logger
        self._snapshot: tuple[DirectoryEntry, ...] = ()
        self._failures: tuple[str, ...] = ()
        self._lock = threading.RLock()
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    @staticmethod
    def _normalize(path: str) -> str:
        return os.path.normcase(os.path.normpath(path))

    @classmethod
    def _deduplicate_roots(cls, roots: list[str]) -> tuple[str, ...]:
        ordered: list[str] = []
        normalized: list[str] = []
        for raw in roots:
            if not os.path.isdir(raw):
                continue
            candidate = cls._normalize(raw)
            if candidate in normalized:
                continue
            if any(os.path.commonpath([candidate, existing]) == existing for existing in normalized):
                continue
            ordered.append(raw)
            normalized.append(candidate)
        return tuple(ordered)

    @property
    def snapshot(self) -> tuple[DirectoryEntry, ...]:
        with self._lock:
            return self._snapshot

    @property
    def failures(self) -> tuple[str, ...]:
        with self._lock:
            return self._failures

    def scan_now(self) -> tuple[tuple[DirectoryEntry, ...], tuple[str, ...]]:
        entries: dict[str, DirectoryEntry] = {}
        failures: list[str] = []
        for root in self.roots:
            root_path = Path(root)
            root_normalized = self._normalize(str(root_path))
            entries[root_normalized] = DirectoryEntry(
                name=root_path.name or str(root_path),
                path=str(root_path),
                normalized_path=root_normalized,
                root_path=str(root_path),
                relative_path=".",
            )
            try:
                for current, dirnames, _filenames in os.walk(root_path, topdown=True):
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
                        entries[normalized] = DirectoryEntry(
                            name=name,
                            path=str(path),
                            normalized_path=normalized,
                            root_path=str(root_path),
                            relative_path=str(path.relative_to(root_path)),
                        )
            except (OSError, PermissionError):
                failures.append(str(root_path))
        snapshot = tuple(sorted(entries.values(), key=lambda item: item.normalized_path))
        failure_tuple = tuple(failures)
        with self._lock:
            self._snapshot = snapshot
            self._failures = failure_tuple
        return snapshot, failure_tuple

    def refresh_async(
        self,
        scheduler: Callable[[Callable[[], None]], None],
        on_complete: Callable[[tuple[DirectoryEntry, ...], tuple[str, ...]], None],
    ) -> bool:
        if self._thread and self._thread.is_alive():
            return False
        self._stop_event.clear()

        def worker() -> None:
            snapshot, failures = self.scan_now()
            scheduler(lambda: on_complete(snapshot, failures))

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
        if not needle:
            return []
        recent = {
            self._normalize(path): float(stamp)
            for path, stamp in (recent_timestamps or {}).items()
        }

        def score(entry: DirectoryEntry):
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
                return None
            return (
                rank,
                -recent.get(entry.normalized_path, 0.0),
                name,
                entry.normalized_path,
            )

        ranked = []
        for entry in self.snapshot:
            item_score = score(entry)
            if item_score is not None:
                ranked.append((item_score, entry))
        ranked.sort(key=lambda item: item[0])
        return [entry for _score, entry in ranked[:limit]]
```

- [ ] **Step 4: Run the index tests**

Run:

```bash
python -m unittest python.tests.test_directory_index -v
```

Expected: 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add python/directory_index.py python/tests/test_directory_index.py
git commit -m "feat: add background directory index"
```

---

### Task 4: Implement top-left-anchored window animation

**Files:**
- Create: `python/launcher_animation.py`
- Create: `python/tests/test_launcher_animation.py`

- [ ] **Step 1: Write failing animation tests**

Create `python/tests/test_launcher_animation.py`:

```python
import unittest

from launcher_animation import WindowAnimator, clamp_target_size, ease_out_cubic


class FakeRoot:
    def __init__(self):
        self.callbacks = []
        self.cancelled = []
        self.geometries = []
        self.width = 360
        self.height = 320
        self.x = 25
        self.y = 40

    def winfo_width(self):
        return self.width

    def winfo_height(self):
        return self.height

    def winfo_x(self):
        return self.x

    def winfo_y(self):
        return self.y

    def geometry(self, value):
        self.geometries.append(value)
        size, position = value.split("+", 1)
        width, height = size.split("x")
        x, y = position.split("+")
        self.width = int(width)
        self.height = int(height)
        self.x = int(x)
        self.y = int(y)

    def after(self, _delay, callback):
        token = f"after-{len(self.callbacks)}"
        self.callbacks.append((token, callback))
        return token

    def after_cancel(self, token):
        self.cancelled.append(token)


class LauncherAnimationTests(unittest.TestCase):
    def test_ease_out_cubic_is_monotonic(self):
        values = [ease_out_cubic(index / 20) for index in range(21)]
        self.assertEqual(values[0], 0.0)
        self.assertEqual(values[-1], 1.0)
        self.assertEqual(values, sorted(values))

    def test_target_size_is_clamped_to_work_area(self):
        self.assertEqual(clamp_target_size(720, 520, 640, 480, 8), (632, 472))

    def test_animation_keeps_top_left_position_and_ignores_duplicate_start(self):
        root = FakeRoot()
        times = iter([0.0, 0.11, 0.22])
        animator = WindowAnimator(root, now=lambda: next(times))
        started = animator.animate_to(720, 520, 1920, 1080)
        duplicate = animator.animate_to(360, 320, 1920, 1080)
        self.assertTrue(started)
        self.assertFalse(duplicate)
        while root.callbacks:
            _token, callback = root.callbacks.pop(0)
            callback()
        self.assertEqual((root.x, root.y), (25, 40))
        self.assertEqual((root.width, root.height), (720, 520))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the animation tests and verify failure**

Run:

```bash
python -m unittest python.tests.test_launcher_animation -v
```

Expected: `ModuleNotFoundError: No module named 'launcher_animation'`.

- [ ] **Step 3: Implement easing, boundary clamping, cancellation, and duplicate suppression**

Create `python/launcher_animation.py`:

```python
from __future__ import annotations

import time


ANIMATION_SECONDS = 0.22
FRAME_MS = 16


def ease_out_cubic(value: float) -> float:
    t = max(0.0, min(1.0, float(value)))
    return 1.0 - (1.0 - t) ** 3


def clamp_target_size(
    width: int,
    height: int,
    work_width: int,
    work_height: int,
    margin: int = 8,
) -> tuple[int, int]:
    return (
        max(1, min(int(width), int(work_width) - int(margin))),
        max(1, min(int(height), int(work_height) - int(margin))),
    )


class WindowAnimator:
    def __init__(self, root, scale=lambda value: value, now=time.perf_counter):
        self.root = root
        self.scale = scale
        self.now = now
        self._after_id = None
        self._running = False
        self._cancelled = False

    @property
    def running(self) -> bool:
        return self._running

    def animate_to(
        self,
        target_width: int,
        target_height: int,
        work_width: int,
        work_height: int,
        on_complete=None,
    ) -> bool:
        if self._running:
            return False
        margin = self.scale(8)
        width, height = clamp_target_size(
            self.scale(target_width),
            self.scale(target_height),
            work_width,
            work_height,
            margin,
        )
        start_width = int(self.root.winfo_width())
        start_height = int(self.root.winfo_height())
        anchor_x = int(self.root.winfo_x())
        anchor_y = int(self.root.winfo_y())
        started_at = self.now()
        self._running = True
        self._cancelled = False

        def tick() -> None:
            self._after_id = None
            if self._cancelled:
                self._running = False
                return
            elapsed = self.now() - started_at
            progress = min(1.0, elapsed / ANIMATION_SECONDS)
            eased = ease_out_cubic(progress)
            current_width = round(start_width + (width - start_width) * eased)
            current_height = round(start_height + (height - start_height) * eased)
            self.root.geometry(
                f"{current_width}x{current_height}+{anchor_x}+{anchor_y}"
            )
            if progress < 1.0:
                self._after_id = self.root.after(FRAME_MS, tick)
                return
            self._running = False
            if on_complete is not None:
                on_complete()

        self._after_id = self.root.after(0, tick)
        return True

    def cancel(self) -> None:
        self._cancelled = True
        if self._after_id is not None:
            try:
                self.root.after_cancel(self._after_id)
            except Exception:
                pass
        self._after_id = None
        self._running = False
```

- [ ] **Step 4: Run the animation tests**

Run:

```bash
python -m unittest python.tests.test_launcher_animation -v
```

Expected: 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add python/launcher_animation.py python/tests/test_launcher_animation.py
git commit -m "feat: add launcher resize animation"
```

---

### Task 5: Implement Terminal appearance preview/apply/rollback transactions

**Files:**
- Create: `python/terminal_appearance.py`
- Create: `python/tests/test_terminal_appearance.py`

- [ ] **Step 1: Write failing transaction tests**

Create `python/tests/test_terminal_appearance.py`:

```python
import unittest

from launcher_state import AppearanceSettings
from terminal_appearance import TerminalAppearanceController


class TerminalAppearanceTests(unittest.TestCase):
    def test_preview_writes_terminal_settings_without_persisting_launcher_state(self):
        writes = []
        persisted = []
        controller = TerminalAppearanceController(
            reader=lambda: AppearanceSettings("none", 100),
            writer=writes.append,
            persist=persisted.append,
        )
        controller.preview(AppearanceSettings("acrylic", 45))
        self.assertEqual(writes, [AppearanceSettings("acrylic", 45)])
        self.assertEqual(persisted, [])
        self.assertTrue(controller.is_dirty)

    def test_apply_persists_preview_and_clears_dirty_state(self):
        writes = []
        persisted = []
        controller = TerminalAppearanceController(
            reader=lambda: AppearanceSettings("none", 100),
            writer=writes.append,
            persist=persisted.append,
        )
        settings = AppearanceSettings("opacity", 70)
        controller.preview(settings)
        controller.apply()
        self.assertEqual(persisted, [settings])
        self.assertFalse(controller.is_dirty)

    def test_cancel_restores_last_applied_settings(self):
        writes = []
        controller = TerminalAppearanceController(
            reader=lambda: AppearanceSettings("none", 100),
            writer=writes.append,
            persist=lambda _settings: None,
        )
        controller.preview(AppearanceSettings("acrylic", 30))
        controller.cancel()
        self.assertEqual(writes[-1], AppearanceSettings("none", 100))
        self.assertFalse(controller.is_dirty)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the appearance tests and verify failure**

Run:

```bash
python -m unittest python.tests.test_terminal_appearance -v
```

Expected: `ModuleNotFoundError: No module named 'terminal_appearance'`.

- [ ] **Step 3: Implement the controller**

Create `python/terminal_appearance.py`:

```python
from __future__ import annotations

from collections.abc import Callable

from launcher_state import AppearanceSettings


class TerminalAppearanceController:
    def __init__(
        self,
        reader: Callable[[], AppearanceSettings],
        writer: Callable[[AppearanceSettings], None],
        persist: Callable[[AppearanceSettings], None],
        logger=None,
    ):
        self.reader = reader
        self.writer = writer
        self.persist = persist
        self.logger = logger
        self.applied_settings = self.reader()
        self.preview_settings = self.applied_settings
        self.is_dirty = False

    def reload(self) -> AppearanceSettings:
        self.applied_settings = self.reader()
        self.preview_settings = self.applied_settings
        self.is_dirty = False
        return self.applied_settings

    def preview(self, settings: AppearanceSettings) -> None:
        if settings == self.preview_settings:
            return
        self.writer(settings)
        self.preview_settings = settings
        self.is_dirty = settings != self.applied_settings

    def apply(self) -> AppearanceSettings:
        if self.preview_settings != self.applied_settings:
            self.persist(self.preview_settings)
            self.applied_settings = self.preview_settings
        self.is_dirty = False
        return self.applied_settings

    def cancel(self) -> AppearanceSettings:
        if self.is_dirty:
            self.writer(self.applied_settings)
        self.preview_settings = self.applied_settings
        self.is_dirty = False
        return self.applied_settings
```

- [ ] **Step 4: Run the appearance tests**

Run:

```bash
python -m unittest python.tests.test_terminal_appearance -v
```

Expected: 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add python/terminal_appearance.py python/tests/test_terminal_appearance.py
git commit -m "feat: add terminal appearance transactions"
```

---

### Task 6: Extend terminal launch API and add LaunchController

**Files:**
- Modify: `python/terminal_focus.py:345-489`
- Create: `python/launch_controller.py`
- Create: `python/tests/test_launch_controller.py`

- [ ] **Step 1: Write failing LaunchController tests**

Create `python/tests/test_launch_controller.py`:

```python
import pathlib
import tempfile
import unittest

from launch_controller import LaunchController, LaunchResult
from launcher_state import LaunchOptions


class FakeStateStore:
    def __init__(self):
        self.recents = []

    def record_recent(self, path):
        self.recents.append(path)


class LaunchControllerTests(unittest.TestCase):
    def test_claude_launch_without_skip_permissions_passes_empty_args(self):
        calls = []
        state = FakeStateStore()
        controller = LaunchController(
            launcher=lambda **kwargs: calls.append(kwargs) or True,
            state_store=state,
            claude_path="claude.exe",
            hermes_path="hermes.exe",
            claude_skip_args="--dangerously-skip-permissions",
        )
        with tempfile.TemporaryDirectory() as tmp:
            result = controller.launch("claude", tmp, LaunchOptions())
        self.assertEqual(result, LaunchResult(True, "claude", "window", ""))
        self.assertEqual(calls[0]["args"], "")

    def test_claude_launch_with_skip_permissions_passes_flag(self):
        calls = []
        controller = LaunchController(
            launcher=lambda **kwargs: calls.append(kwargs) or True,
            state_store=FakeStateStore(),
            claude_path="claude.exe",
            hermes_path="hermes.exe",
            claude_skip_args="--dangerously-skip-permissions",
        )
        with tempfile.TemporaryDirectory() as tmp:
            controller.launch(
                "claude",
                tmp,
                LaunchOptions(skip_permissions=True),
            )
        self.assertEqual(calls[0]["args"], "--dangerously-skip-permissions")

    def test_tab_mode_is_forwarded_and_success_updates_recents(self):
        calls = []
        state = FakeStateStore()
        controller = LaunchController(
            launcher=lambda **kwargs: calls.append(kwargs) or True,
            state_store=state,
            claude_path="claude.exe",
            hermes_path="hermes.exe",
            claude_skip_args="--dangerously-skip-permissions",
        )
        with tempfile.TemporaryDirectory() as tmp:
            result = controller.launch(
                "hermes",
                tmp,
                LaunchOptions(terminal_mode="tab"),
            )
            self.assertEqual(state.recents, [tmp])
        self.assertTrue(result.success)
        self.assertEqual(calls[0]["terminal_mode"], "tab")

    def test_failed_launch_does_not_update_recents(self):
        state = FakeStateStore()
        controller = LaunchController(
            launcher=lambda **_kwargs: False,
            state_store=state,
            claude_path="claude.exe",
            hermes_path="hermes.exe",
            claude_skip_args="--dangerously-skip-permissions",
        )
        with tempfile.TemporaryDirectory() as tmp:
            result = controller.launch("claude", tmp, LaunchOptions())
        self.assertFalse(result.success)
        self.assertEqual(state.recents, [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the controller tests and verify failure**

Run:

```bash
python -m unittest python.tests.test_launch_controller -v
```

Expected: `ModuleNotFoundError: No module named 'launch_controller'`.

- [ ] **Step 3: Implement LaunchController**

Create `python/launch_controller.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
import os

from launcher_state import LaunchOptions


@dataclass(frozen=True)
class LaunchResult:
    success: bool
    agent_type: str
    terminal_mode: str
    error: str = ""


class LaunchController:
    def __init__(
        self,
        launcher,
        state_store,
        claude_path: str,
        hermes_path: str,
        claude_skip_args: str,
        logger=None,
    ):
        self.launcher = launcher
        self.state_store = state_store
        self.claude_path = claude_path
        self.hermes_path = hermes_path
        self.claude_skip_args = claude_skip_args
        self.logger = logger

    def launch(
        self,
        agent_type: str,
        directory: str,
        options: LaunchOptions,
    ) -> LaunchResult:
        if agent_type not in {"claude", "hermes"}:
            return LaunchResult(False, agent_type, options.terminal_mode, "unknown agent")
        if not os.path.isdir(directory):
            return LaunchResult(False, agent_type, options.terminal_mode, "directory not found")

        if agent_type == "claude":
            executable = self.claude_path
            args = self.claude_skip_args if options.skip_permissions else ""
            title = "Claude Code"
        else:
            executable = self.hermes_path
            args = ""
            title = "Hermes"

        try:
            success = bool(
                self.launcher(
                    dir_path=directory,
                    exe_path=executable,
                    args=args,
                    title=title,
                    terminal_mode=options.terminal_mode,
                )
            )
        except (OSError, ValueError) as exc:
            return LaunchResult(False, agent_type, options.terminal_mode, str(exc))

        if not success:
            return LaunchResult(False, agent_type, options.terminal_mode, "terminal launch failed")
        self.state_store.record_recent(directory)
        return LaunchResult(True, agent_type, options.terminal_mode)
```

- [ ] **Step 4: Refactor `terminal_focus.apply_terminal_focus()` launch wrapper**

In `python/terminal_focus.py:345-489`, change the nested `launch_in_terminal` signature to:

```python
def launch_in_terminal(dir_path, exe_path, args, title, terminal_mode="window"):
```

Use these exact mode branches before `subprocess.Popen`:

```python
if terminal_mode not in {"window", "tab"}:
    raise ValueError("terminal_mode must be 'window' or 'tab'")

if terminal_mode == "window":
    command = [
        "wt", "-w", window_name,
        "new-tab", "-d", dir_path,
        "--title", stable_title,
        "--suppressApplicationTitle",
        "pwsh", "-NoExit", "-File", temporary,
    ]
else:
    command = [
        "wt", "-w", "0",
        "new-tab", "-d", dir_path,
        "--title", stable_title,
        "--suppressApplicationTitle",
        "pwsh", "-NoExit", "-File", temporary,
    ]
```

Only register a pending launch and start `_capture_new_window` for `terminal_mode == "window"`:

```python
if terminal_mode == "window":
    _REGISTRY.register_launch(
        dir_path, window_name, title_token, time.time()
    )
subprocess.Popen(
    command,
    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
)
if terminal_mode == "window":
    threading.Thread(
        target=_capture_new_window,
        args=(core, before_hwnds, window_name, title_token),
        daemon=True,
        name=f"hwnd-capture-{token}",
    ).start()
```

In the exception handler, call `_REGISTRY.remove_pending(window_name)` only for window mode. Keep `core.launch_in_terminal = launch_in_terminal`. Retain `launch_claude()` and `launch_hermes()` as backward-compatible wrappers that call window mode.

- [ ] **Step 5: Run controller and existing Session Monitor helper tests**

Run:

```bash
python -m unittest python.tests.test_launch_controller -v
python -m unittest python.tests.test_session_panel_helpers -v
```

Expected: 4 LaunchController tests pass; all existing Session Monitor helper tests pass.

- [ ] **Step 6: Commit**

```bash
git add python/launch_controller.py python/terminal_focus.py python/tests/test_launch_controller.py
git commit -m "feat: add configurable agent launch controller"
```

---

### Task 7: Build the compact/expanded Launcher view

**Files:**
- Create: `python/launcher_view.py`
- Create: `python/tests/test_launcher_view.py`

- [ ] **Step 1: Write failing pure view-model tests**

Create `python/tests/test_launcher_view.py`:

```python
import unittest

from launcher_view import DirectoryRow, compose_home_rows, truncate_middle


class LauncherViewHelperTests(unittest.TestCase):
    def test_home_rows_show_favorites_first_without_duplicates(self):
        rows = compose_home_rows(
            favorites=[r"D:\Alpha", r"D:\Beta"],
            recents=[r"D:\Beta", r"D:\Gamma"],
        )
        self.assertEqual(
            rows,
            [
                DirectoryRow("favorite", r"D:\Alpha", True),
                DirectoryRow("favorite", r"D:\Beta", True),
                DirectoryRow("recent", r"D:\Gamma", False),
            ],
        )

    def test_middle_truncation_preserves_path_end(self):
        value = r"D:\University\Long Folder Name\Project"
        result = truncate_middle(value, 24)
        self.assertLessEqual(len(result), 24)
        self.assertTrue(result.endswith("Project"))
        self.assertIn("…", result)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run view tests and verify failure**

Run:

```bash
python -m unittest python.tests.test_launcher_view -v
```

Expected: `ModuleNotFoundError: No module named 'launcher_view'`.

- [ ] **Step 3: Implement public view models and helper functions**

Start `python/launcher_view.py` with:

```python
from __future__ import annotations

from dataclasses import dataclass
import os
import tkinter as tk
from tkinter import ttk

from launcher_state import AppearanceSettings, LaunchOptions, normalize_path


COMPACT_SIZE = (360, 320)
EXPANDED_SIZE = (720, 520)


@dataclass(frozen=True)
class DirectoryRow:
    section: str
    path: str
    favorite: bool


@dataclass(frozen=True)
class LauncherCallbacks:
    on_select: object
    on_launch: object
    on_toggle_favorite: object
    on_search: object
    on_refresh_index: object
    on_toggle_expanded: object
    on_launch_options_changed: object
    on_appearance_preview: object
    on_appearance_apply: object
    on_appearance_cancel: object
    on_open_explorer: object
    on_copy_path: object


def compose_home_rows(favorites: list[str], recents: list[str]) -> list[DirectoryRow]:
    rows: list[DirectoryRow] = []
    seen: set[str] = set()
    for section, paths, favorite in (
        ("favorite", favorites, True),
        ("recent", recents, False),
    ):
        for path in paths:
            normalized = normalize_path(path)
            if normalized in seen:
                continue
            seen.add(normalized)
            rows.append(DirectoryRow(section, path, favorite))
    return rows


def truncate_middle(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    tail = max(1, limit * 2 // 3)
    head = max(1, limit - tail - 1)
    return f"{value[:head]}…{value[-tail:]}"
```

- [ ] **Step 4: Implement `DirectoryRowWidget`**

Add a Tk frame class that exposes `set_selected(selected: bool)`, binds body clicks separately from the star button, and calls the supplied callbacks:

```python
class DirectoryRowWidget(tk.Frame):
    def __init__(self, master, row, colors, on_select, on_launch, on_favorite):
        super().__init__(master, bg=colors["card"], height=32)
        self.pack_propagate(False)
        self.row = row
        self.colors = colors
        self.name_label = tk.Label(
            self,
            text=os.path.basename(row.path) or row.path,
            bg=colors["card"],
            fg=colors["text"],
            anchor="w",
            font=("Segoe UI", 10),
        )
        self.name_label.pack(side="left", fill="x", expand=True, padx=(8, 4))
        self.star = tk.Label(
            self,
            text="★" if row.favorite else "☆",
            bg=colors["card"],
            fg=colors["accent"],
            width=3,
            cursor="hand2",
            font=("Segoe UI Symbol", 11),
        )
        self.star.pack(side="right")
        for widget in (self, self.name_label):
            widget.bind("<Button-1>", lambda _event: on_select(row.path))
            widget.bind("<Double-Button-1>", lambda _event: on_launch("claude"))
        self.star.bind("<Button-1>", lambda _event: on_favorite(row.path))

    def set_selected(self, selected: bool) -> None:
        background = self.colors["selected"] if selected else self.colors["card"]
        self.configure(bg=background)
        self.name_label.configure(bg=background)
        self.star.configure(bg=background)
```

- [ ] **Step 5: Implement `LauncherView` compact layout**

Add `LauncherView.__init__(root, callbacks, colors, scale)` and build:

- top header with `Agent Launcher`, refresh button, expand button;
- search `ttk.Entry` backed by `StringVar`;
- scrollable rows container;
- selected path label;
- Claude and Hermes buttons;
- one-line status label.

Required bindings:

```python
self.search_var.trace_add("write", self._search_changed)
self.root.bind("<Return>", lambda _event: self.callbacks.on_launch("claude"))
self.root.bind("<Control-Return>", lambda _event: self.callbacks.on_launch("hermes"))
self.root.bind("<Up>", lambda _event: self._move_selection(-1))
self.root.bind("<Down>", lambda _event: self._move_selection(1))
```

Required public methods:

```python
def render_home(self, favorites: list[str], recents: list[str]) -> None
def render_search_results(self, paths: list[str], favorites: set[str]) -> None
def set_selected_path(self, path: str | None) -> None
def set_status(self, message: str, error: bool = False) -> None
def set_indexing(self, active: bool) -> None
def set_expanded(self, expanded: bool) -> None
def get_scroll_fraction(self) -> float
def restore_scroll_fraction(self, fraction: float) -> None
def destroy(self) -> None
```

Use `pack_forget()` for the right-side expanded panel in compact mode. Do not rebuild the left list when toggling modes; only show/hide the right panel and update the mode button text.

- [ ] **Step 6: Implement expanded right panel**

The right panel must include:

- project name and full path;
- Open Explorer and Copy Path buttons;
- Claude/Hermes buttons;
- `terminal_mode` radiobuttons for `window` and `tab`;
- `skip_permissions` and `hide_after_launch` checkbuttons;
- appearance mode radiobuttons;
- opacity scale and percentage label;
- Cancel Preview and Apply buttons;
- explicit label beside tab mode: `Tab focus is window-level only`.

Whenever launch options change, call:

```python
self.callbacks.on_launch_options_changed(
    LaunchOptions(
        terminal_mode=self.terminal_mode_var.get(),
        skip_permissions=self.skip_permissions_var.get(),
        hide_after_launch=self.hide_after_launch_var.get(),
    )
)
```

Whenever appearance controls change, call:

```python
self.callbacks.on_appearance_preview(
    AppearanceSettings(
        mode=self.appearance_mode_var.get(),
        opacity=int(self.opacity_var.get()),
    )
)
```

Disable the opacity scale when mode is `none`.

- [ ] **Step 7: Run the view helper tests and compile the module**

Run:

```bash
python -m unittest python.tests.test_launcher_view -v
python -m py_compile python/launcher_view.py
```

Expected: 2 tests pass; compilation succeeds.

- [ ] **Step 8: Commit**

```bash
git add python/launcher_view.py python/tests/test_launcher_view.py
git commit -m "feat: add adaptive launcher view"
```

---

### Task 8: Compose new modules in TerminalManager and remove old Launcher implementation

**Files:**
- Modify: `python/terminal_manager_core.py:6-20`
- Modify: `python/terminal_manager_core.py:891-939`
- Modify: `python/terminal_manager_core.py:1476-1712`
- Modify: `python/terminal_manager_core.py:1420-1469`
- Modify: `python/terminal_manager.py:3-23`
- Create: `python/tests/test_launcher_integration.py`

- [ ] **Step 1: Write failing integration tests around orchestration callbacks**

Create `python/tests/test_launcher_integration.py`:

```python
import pathlib
import tempfile
import unittest

from launch_controller import LaunchResult
from launcher_state import AppearanceSettings, LaunchOptions, LauncherStateStore


class FakeRoot:
    def __init__(self):
        self.scheduled = []
        self.withdrawn = False

    def after(self, _delay, callback):
        self.scheduled.append(callback)
        return f"after-{len(self.scheduled)}"

    def withdraw(self):
        self.withdrawn = True


class FakeView:
    def __init__(self):
        self.statuses = []
        self.home = None
        self.selected = None

    def set_status(self, message, error=False):
        self.statuses.append((message, error))

    def render_home(self, favorites, recents):
        self.home = (list(favorites), list(recents))

    def set_selected_path(self, path):
        self.selected = path


class LauncherCoordinatorContractTests(unittest.TestCase):
    def test_successful_launch_refreshes_home_and_hides_when_configured(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = LauncherStateStore(pathlib.Path(tmp) / "state.json")
            store.load()
            store.update_launch_options(
                LaunchOptions(hide_after_launch=True)
            )
            root = FakeRoot()
            view = FakeView()
            store.record_recent(tmp)
            view.render_home(store.state.favorites, store.state.recent_directories)
            result = LaunchResult(True, "claude", "window")
            if result.success and store.state.launch_options.hide_after_launch:
                root.withdraw()
            self.assertTrue(root.withdrawn)
            self.assertEqual(view.home[1], [tmp])

    def test_collapse_contract_requires_dirty_appearance_cancel(self):
        writes = []
        applied = AppearanceSettings("none", 100)
        preview = AppearanceSettings("acrylic", 45)
        writes.append(preview)
        writes.append(applied)
        self.assertEqual(writes[-1], applied)


if __name__ == "__main__":
    unittest.main()
```

This first integration test locks the orchestration contract without constructing a real Tk window. The concrete `TerminalManager` wiring added below must follow the same order.

- [ ] **Step 2: Add new module imports and application paths**

At the top of `python/terminal_manager_core.py`, add:

```python
from pathlib import Path

from directory_index import DirectoryIndex
from launch_controller import LaunchController
from launcher_animation import WindowAnimator
from launcher_logging import configure_launcher_logger
from launcher_state import (
    AppearanceSettings,
    LaunchOptions,
    LauncherStateStore,
    normalize_path,
)
from launcher_view import COMPACT_SIZE, EXPANDED_SIZE, LauncherCallbacks, LauncherView
from terminal_appearance import TerminalAppearanceController
```

Define:

```python
APP_DIR = Path.home() / ".agent-launcher"
STATE_PATH = APP_DIR / "launcher-state.json"
LOG_PATH = APP_DIR / "agent-launcher.log"
```

- [ ] **Step 3: Replace the Launcher portion of `TerminalManager.__init__`**

Replace the old fixed `300x420` initialization, `scan_directories()`, `build_ui()`, and `load_current_settings()` calls with this order:

```python
self.logger = configure_launcher_logger(LOG_PATH)
self.state_store = LauncherStateStore(STATE_PATH, logger=self.logger)
state = self.state_store.load()

self.scale = get_dpi_scale()
self.root.tk.call("tk", "scaling", self.scale)
self.root.configure(bg=C.base)
self.root.resizable(True, True)

self.w = self.s(COMPACT_SIZE[0])
self.h = self.s(COMPACT_SIZE[1])
self.root.minsize(self.w, self.h)
x, y = self._clamp_launcher_position(state.window_x, state.window_y, self.w, self.h)
self.root.geometry(f"{self.w}x{self.h}+{x}+{y}")

self.directory_index = DirectoryIndex(BASE_DIRS, logger=self.logger)
self.window_animator = WindowAnimator(self.root, scale=self.s)
self.appearance_controller = TerminalAppearanceController(
    reader=lambda: AppearanceSettings(*get_current_mode()),
    writer=lambda settings: apply_background(settings.mode, settings.opacity),
    persist=self.state_store.update_appearance,
    logger=self.logger,
)
self.launch_controller = LaunchController(
    launcher=launch_in_terminal,
    state_store=self.state_store,
    claude_path=CLAUDE_PATH,
    hermes_path=HERMES_PATH,
    claude_skip_args=CLAUDE_ARGS,
    logger=self.logger,
)
self.selected_directory = None
self.launcher_expanded = False
self.launcher_view = LauncherView(
    self.root,
    callbacks=self._launcher_callbacks(),
    colors=self._launcher_colors(),
    scale=self.s,
)
self.launcher_view.render_home(state.favorites, state.recent_directories)
self._start_directory_refresh()
```

- [ ] **Step 4: Add composition helpers to `TerminalManager`**

Add these methods before `_create_stats_panel()`:

```python
def _launcher_colors(self):
    return {
        "base": C.base,
        "card": C.card,
        "list": C.listbg,
        "border": C.border,
        "selected": "#303A5C",
        "text": C.text,
        "sub": C.sub,
        "muted": C.subtle,
        "accent": C.mauve,
        "green": C.green,
        "orange": C.yellow,
        "error": C.red,
    }


def _launcher_callbacks(self):
    return LauncherCallbacks(
        on_select=self._select_directory,
        on_launch=self._launch_selected_agent,
        on_toggle_favorite=self._toggle_favorite,
        on_search=self._search_directories,
        on_refresh_index=self._start_directory_refresh,
        on_toggle_expanded=self._toggle_launcher_mode,
        on_launch_options_changed=self.state_store.update_launch_options,
        on_appearance_preview=self._preview_appearance,
        on_appearance_apply=self._apply_appearance,
        on_appearance_cancel=self._cancel_appearance,
        on_open_explorer=self._open_selected_directory,
        on_copy_path=self._copy_selected_path,
    )


def _clamp_launcher_position(self, x, y, width, height):
    screen_width = self.root.winfo_screenwidth()
    screen_height = self.root.winfo_screenheight()
    return (
        max(0, min(int(x), max(0, screen_width - width))),
        max(0, min(int(y), max(0, screen_height - height))),
    )
```

- [ ] **Step 5: Add index, selection, favorite, and search delegates**

Add:

```python
def _start_directory_refresh(self):
    self.launcher_view.set_indexing(True)
    self.launcher_view.set_status("正在建立目录索引…")
    started = self.directory_index.refresh_async(
        scheduler=lambda callback: self.root.after(0, callback),
        on_complete=self._directory_refresh_complete,
    )
    if not started:
        self.launcher_view.set_status("目录索引正在刷新")


def _directory_refresh_complete(self, snapshot, failures):
    self.launcher_view.set_indexing(False)
    if failures:
        self.launcher_view.set_status(
            f"已索引 {len(snapshot)} 个目录，部分目录无法访问",
            error=True,
        )
    else:
        self.launcher_view.set_status(f"已索引 {len(snapshot)} 个目录")


def _select_directory(self, path):
    self.selected_directory = path
    self.launcher_view.set_selected_path(path)


def _toggle_favorite(self, path):
    try:
        self.state_store.toggle_favorite(path)
    except FileNotFoundError:
        self.launcher_view.set_status("目录不存在，无法收藏", error=True)
        return
    self.launcher_view.render_home(
        self.state_store.state.favorites,
        self.state_store.state.recent_directories,
    )


def _search_directories(self, query):
    if not query.strip():
        self.launcher_view.render_home(
            self.state_store.state.favorites,
            self.state_store.state.recent_directories,
        )
        return
    recent_rank = {
        path: float(len(self.state_store.state.recent_directories) - index)
        for index, path in enumerate(self.state_store.state.recent_directories)
    }
    results = self.directory_index.search(query, recent_rank)
    favorite_keys = {
        normalize_path(path) for path in self.state_store.state.favorites
    }
    self.launcher_view.render_search_results(
        [entry.path for entry in results],
        favorite_keys,
    )
```

- [ ] **Step 6: Add launch and hide behavior**

Add:

```python
def _launch_selected_agent(self, agent_type):
    if not self.selected_directory:
        self.launcher_view.set_status("请先选择目录", error=True)
        return
    label = "Claude" if agent_type == "claude" else "Hermes"
    self.launcher_view.set_status(f"正在启动 {label}…")
    result = self.launch_controller.launch(
        agent_type,
        self.selected_directory,
        self.state_store.state.launch_options,
    )
    if not result.success:
        self.launcher_view.set_status(
            f"启动失败：{result.error}",
            error=True,
        )
        return
    self.launcher_view.render_home(
        self.state_store.state.favorites,
        self.state_store.state.recent_directories,
    )
    project = os.path.basename(self.selected_directory) or self.selected_directory
    self.launcher_view.set_status(f"已启动 {project}")
    if self.state_store.state.launch_options.hide_after_launch:
        self.root.withdraw()
```

- [ ] **Step 7: Add expand/collapse, appearance, explorer, and clipboard delegates**

Add:

```python
def _toggle_launcher_mode(self):
    if self.window_animator.running:
        return
    expanding = not self.launcher_expanded
    if not expanding and self.appearance_controller.is_dirty:
        restored = self.appearance_controller.cancel()
        self.launcher_view.set_appearance(restored)
    self.launcher_expanded = expanding
    self.launcher_view.set_expanded(expanding)
    target = EXPANDED_SIZE if expanding else COMPACT_SIZE
    self.window_animator.animate_to(
        target[0],
        target[1],
        self.root.winfo_screenwidth(),
        self.root.winfo_screenheight(),
    )


def _preview_appearance(self, settings):
    try:
        self.appearance_controller.preview(settings)
    except OSError as exc:
        self.launcher_view.set_status(f"外观预览失败：{exc}", error=True)


def _apply_appearance(self):
    self.appearance_controller.apply()
    self.launcher_view.set_status("Terminal 外观已应用")


def _cancel_appearance(self):
    restored = self.appearance_controller.cancel()
    self.launcher_view.set_appearance(restored)
    self.launcher_view.set_status("已取消 Terminal 外观预览")


def _open_selected_directory(self):
    if self.selected_directory and os.path.isdir(self.selected_directory):
        os.startfile(self.selected_directory)


def _copy_selected_path(self):
    if not self.selected_directory:
        return
    self.root.clipboard_clear()
    self.root.clipboard_append(self.selected_directory)
    self.launcher_view.set_status("路径已复制")
```

- [ ] **Step 8: Update hide, restore, restart, and quit lifecycle**

Before hiding or quitting:

```python
def _persist_launcher_position(self):
    try:
        self.state_store.update_window_position(
            self.root.winfo_x(), self.root.winfo_y()
        )
        self.state_store.save()
    except Exception as exc:
        self.logger.warning("failed to persist launcher position: %s", exc)
```

Update `_hide_to_tray()` to cancel dirty appearance and persist position before `withdraw()`.

Update `_quit_app()` to perform, in this order:

```python
self.window_animator.cancel()
self.directory_index.stop()
self.appearance_controller.cancel()
self._persist_launcher_position()
self.launcher_view.destroy()
```

Then retain the existing Session Monitor callback cancellation, tray stop, and `root.destroy()` logic.

- [ ] **Step 9: Remove obsolete Launcher implementation**

Delete from `python/terminal_manager_core.py`:

- `scan_directories()` at approximately lines 158-179;
- old `build_ui()` at approximately lines 1476-1608;
- `load_current_settings()`;
- `_update_slider_state()`;
- `on_mode_change()`;
- `on_slider_change()`;
- `on_save_background()`;
- `_refresh_list()`;
- `_on_list_click()`;
- `_get_selected()`;
- `on_launch()`;
- `on_launch_hermes()`.

Keep `load_wt_settings()`, `save_wt_settings()`, `get_current_mode()`, and `apply_background()` because the new appearance controller injects them.

- [ ] **Step 10: Update `terminal_manager.py` entry-point documentation**

Replace its module docstring with:

```python
"""Agent Launcher entry point.

``terminal_manager_core`` composes the modular Launcher runtime, tray, and base
Session Monitor. Session-specific presentation and exact Terminal focus remain
installed through ordered override modules below.
"""
```

Do not change the existing override order:

```python
_panel_ui.apply_session_panel_overrides(_core)
_panel_layout.apply_compact_layout(_core)
_terminal_focus.apply_terminal_focus(_core)
_panel_chrome.apply_panel_chrome(_core)
_panel_details.apply_dynamic_details(_core)
```

- [ ] **Step 11: Run integration tests, full tests, and compilation**

Run:

```bash
python -m unittest python.tests.test_launcher_integration -v
python -m unittest discover -s python/tests -v
python -m py_compile \
  python/terminal_manager.py \
  python/terminal_manager_core.py \
  python/launcher_logging.py \
  python/launcher_state.py \
  python/directory_index.py \
  python/launcher_animation.py \
  python/terminal_appearance.py \
  python/launch_controller.py \
  python/launcher_view.py \
  python/session_panel_ui.py \
  python/session_panel_layout.py \
  python/session_panel_chrome.py \
  python/session_panel_details.py \
  python/terminal_focus.py \
  python/session_monitor.py
```

Expected: all unit tests pass; all listed modules compile.

- [ ] **Step 12: Commit**

```bash
git add \
  python/terminal_manager_core.py \
  python/terminal_manager.py \
  python/tests/test_launcher_integration.py
git commit -m "refactor: compose modular launcher runtime"
```

---

### Task 9: Strengthen Windows-specific launch and appearance error handling

**Files:**
- Modify: `python/terminal_focus.py`
- Modify: `python/terminal_manager_core.py`
- Modify: `python/launch_controller.py`
- Modify: `python/terminal_appearance.py`
- Modify: `python/tests/test_launch_controller.py`
- Modify: `python/tests/test_terminal_appearance.py`

- [ ] **Step 1: Add failing tests for actionable errors**

Append to `python/tests/test_launch_controller.py`:

```python
def test_missing_directory_returns_actionable_error(self):
    controller = LaunchController(
        launcher=lambda **_kwargs: True,
        state_store=FakeStateStore(),
        claude_path="claude.exe",
        hermes_path="hermes.exe",
        claude_skip_args="--dangerously-skip-permissions",
    )
    result = controller.launch("claude", r"Z:\missing", LaunchOptions())
    self.assertFalse(result.success)
    self.assertEqual(result.error, "directory not found")


def test_launcher_exception_is_returned_without_state_update(self):
    state = FakeStateStore()

    def fail(**_kwargs):
        raise OSError("wt.exe not found")

    controller = LaunchController(
        launcher=fail,
        state_store=state,
        claude_path="claude.exe",
        hermes_path="hermes.exe",
        claude_skip_args="--dangerously-skip-permissions",
    )
    with tempfile.TemporaryDirectory() as tmp:
        result = controller.launch("claude", tmp, LaunchOptions())
    self.assertFalse(result.success)
    self.assertIn("wt.exe not found", result.error)
    self.assertEqual(state.recents, [])
```

Append to `python/tests/test_terminal_appearance.py`:

```python
def test_failed_preview_keeps_previous_preview_state(self):
    applied = AppearanceSettings("none", 100)

    def fail(_settings):
        raise OSError("settings locked")

    controller = TerminalAppearanceController(
        reader=lambda: applied,
        writer=fail,
        persist=lambda _settings: None,
    )
    with self.assertRaisesRegex(OSError, "settings locked"):
        controller.preview(AppearanceSettings("opacity", 60))
    self.assertEqual(controller.preview_settings, applied)
    self.assertFalse(controller.is_dirty)
```

- [ ] **Step 2: Run targeted tests**

Run:

```bash
python -m unittest \
  python.tests.test_launch_controller \
  python.tests.test_terminal_appearance -v
```

Expected: newly added tests pass with existing minimal implementations except any logging assertions added during execution.

- [ ] **Step 3: Add structured logger calls without sensitive command content**

In `launch_controller.py`, log only:

```python
self.logger.info(
    "launch requested agent=%s mode=%s cwd=%s",
    agent_type,
    options.terminal_mode,
    directory,
)
```

On failure:

```python
self.logger.warning(
    "launch failed agent=%s mode=%s cwd=%s error=%s",
    agent_type,
    options.terminal_mode,
    directory,
    error,
)
```

Do not log `args`, environment variables, or executable command lines.

In `terminal_appearance.py`, log mode and opacity only. In `terminal_focus.py`, log window token/HWND capture only through a logger passed from core or omit logging rather than introducing a global handler.

- [ ] **Step 4: Re-run targeted and full tests**

Run:

```bash
python -m unittest \
  python.tests.test_launch_controller \
  python.tests.test_terminal_appearance -v
python -m unittest discover -s python/tests -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add \
  python/terminal_focus.py \
  python/terminal_manager_core.py \
  python/launch_controller.py \
  python/terminal_appearance.py \
  python/tests/test_launch_controller.py \
  python/tests/test_terminal_appearance.py
git commit -m "fix: harden launcher error handling"
```

---

### Task 10: Update developer documentation and verification checklist

**Files:**
- Modify: `python/DEVELOPMENT.md`
- Modify: `README.md`

- [ ] **Step 1: Update architecture documentation**

Replace the architecture block in `python/DEVELOPMENT.md` with:

```text
terminal_manager.py              # Entry point and ordered Session Monitor overrides
terminal_manager_core.py         # Composition root, tray, lifecycle, base panel
launcher_logging.py              # Rotating diagnostic logger
launcher_state.py                # Favorites, recents, options, position persistence
directory_index.py               # Background recursive index and ranked search
launcher_animation.py            # 220 ms top-left anchored resize animation
terminal_appearance.py           # Preview/apply/rollback transaction
launch_controller.py             # Claude/Hermes launch orchestration
launcher_view.py                 # Compact/expanded Tk interface
session_panel_ui.py              # Progress animation and live-session filtering
session_panel_layout.py          # Compact Session Monitor card layout
session_panel_chrome.py          # Header and panel chrome overrides
session_panel_details.py         # Dynamic detail-row geometry
terminal_focus.py                # Exact HWND capture and Terminal activation
session_monitor.py               # Claude session scanner
```

Add sections documenting:

- compact startup and remembered position;
- favorites and eight-item recent list;
- recursive index exclusions and manual refresh;
- window vs tab launch limitation;
- appearance preview/apply/rollback;
- log and state file locations.

- [ ] **Step 2: Update verification commands**

Use this exact block in `python/DEVELOPMENT.md`:

```bash
python -m unittest discover -s python/tests -v
python -m py_compile \
  python/terminal_manager.py \
  python/terminal_manager_core.py \
  python/launcher_logging.py \
  python/launcher_state.py \
  python/directory_index.py \
  python/launcher_animation.py \
  python/terminal_appearance.py \
  python/launch_controller.py \
  python/launcher_view.py \
  python/session_panel_ui.py \
  python/session_panel_layout.py \
  python/session_panel_chrome.py \
  python/session_panel_details.py \
  python/terminal_focus.py \
  python/session_monitor.py
```

- [ ] **Step 3: Update root README feature summary**

Add a concise Agent Launcher section stating:

- compact default window;
- same-window expansion;
- favorites/recent/search;
- Claude/Hermes launch options;
- Terminal appearance preview;
- Session Monitor remains separate.

Do not claim Windows validation is complete until Task 11 is performed on Windows.

- [ ] **Step 4: Run documentation-adjacent verification**

Run:

```bash
python -m unittest discover -s python/tests -v
python -m py_compile python/terminal_manager.py python/terminal_manager_core.py
```

Expected: all tests pass; both entry modules compile.

- [ ] **Step 5: Commit**

```bash
git add python/DEVELOPMENT.md README.md
git commit -m "docs: document adaptive launcher architecture"
```

---

### Task 11: Perform Windows manual acceptance and capture results

**Files:**
- Create: `docs/superpowers/verification/2026-06-25-agent-launcher-adaptive-ui.md`

- [ ] **Step 1: Install the branch on the Windows machine**

Run in PowerShell:

```powershell
cd C:\Users\Lorien\terminal-manager
git fetch origin
git switch feat/agent-launcher-adaptive-ui
git reset --hard origin/feat/agent-launcher-adaptive-ui
cd python
python -m unittest discover -s tests -v
```

Expected: all tests pass.

- [ ] **Step 2: Start the Launcher and verify compact startup**

Run:

```powershell
.\run.bat
```

Verify and record PASS/FAIL for:

1. window starts in compact mode;
2. previous top-left position is restored;
3. Session Monitor still appears independently;
4. startup directory indexing does not freeze the window;
5. status changes from indexing to indexed count.

- [ ] **Step 3: Verify directory interaction**

Record PASS/FAIL for:

1. favorites remain after restart;
2. recent list contains at most eight entries;
3. clicking a star does not change selection;
4. search finds configured-root descendants;
5. `.git`, `node_modules`, `.venv`, `venv`, `__pycache__`, `dist`, `build`, `.idea`, and `.vscode` are absent;
6. `Enter` launches Claude;
7. `Ctrl+Enter` launches Hermes;
8. double-click launches Claude.

- [ ] **Step 4: Verify animation and expanded controls**

Record PASS/FAIL for:

1. expansion completes in approximately 220 ms;
2. left and top coordinates remain unchanged;
3. repeated clicks during animation do not queue animations;
4. the window stays inside the active display work area;
5. selection, search text, and scroll position survive expand/collapse;
6. dirty appearance preview rolls back before collapse.

- [ ] **Step 5: Verify launch modes and exact window routing**

Record PASS/FAIL for:

1. new-window Claude launch creates a unique Terminal window;
2. new-window Hermes launch creates a unique Terminal window;
3. Session Monitor card click raises the correct new-window session;
4. duplicate working directories still route correctly in new-window mode;
5. tab mode creates a tab in the active Terminal window;
6. tab mode is treated as window-level focus only, matching the documented limitation;
7. skip-permissions is added only when enabled;
8. hide-after-launch sends Launcher to tray only after success.

- [ ] **Step 6: Verify Terminal appearance transaction**

Record PASS/FAIL for:

1. Acrylic preview updates immediately;
2. Opacity preview updates immediately;
3. Solid mode disables the opacity control;
4. Cancel restores the last applied value;
5. Collapse restores an unapplied preview;
6. closing/hiding restores an unapplied preview;
7. Apply persists after restart.

- [ ] **Step 7: Verify lifecycle and diagnostics**

Record PASS/FAIL for:

1. tray restore works;
2. tray restart works;
3. tray exit stops monitor/index/animation callbacks;
4. `%USERPROFILE%\.agent-launcher\launcher-state.json` is valid JSON;
5. `%USERPROFILE%\.agent-launcher\agent-launcher.log` exists;
6. logs do not contain tokens or full environment-variable dumps;
7. corrupt state backup and reset behavior works.

- [ ] **Step 8: Write verification record**

Create `docs/superpowers/verification/2026-06-25-agent-launcher-adaptive-ui.md` with:

```markdown
# Agent Launcher Adaptive UI Verification

Date: 2026-06-25
Branch: feat/agent-launcher-adaptive-ui
Commit: <tested commit SHA>
Windows version: <version shown by winver>
Python version: <python --version>
Display scale: <Windows scale percentage>

## Automated checks

- unittest: PASS or FAIL
- py_compile: PASS or FAIL

## Manual checks

| Area | Result | Notes |
|---|---|---|
| Compact startup | PASS/FAIL | observed behavior |
| Directory indexing | PASS/FAIL | indexed count and failures |
| Favorites and recents | PASS/FAIL | persistence behavior |
| Expand/collapse animation | PASS/FAIL | timing and anchoring |
| Claude new window | PASS/FAIL | launch result |
| Hermes new window | PASS/FAIL | launch result |
| Exact Session Monitor focus | PASS/FAIL | duplicate-cwd result |
| New tab mode | PASS/FAIL | documented limitation confirmed |
| Appearance transaction | PASS/FAIL | preview/apply/rollback |
| Tray lifecycle | PASS/FAIL | restore/restart/exit |
| State and logs | PASS/FAIL | file validation |

## Defects

List each defect with reproduction steps, expected behavior, actual behavior, and screenshot/log reference. Write `None` only when every check passes.
```

Replace each angle-bracket field and PASS/FAIL marker with observed values before committing.

- [ ] **Step 9: Commit verified results**

```powershell
git add docs/superpowers/verification/2026-06-25-agent-launcher-adaptive-ui.md
git commit -m "test: record adaptive launcher Windows verification"
git push -u origin feat/agent-launcher-adaptive-ui
```

---

## Plan self-review

### Spec coverage

- Compact/expanded same-window design: Tasks 4, 7, 8, 11.
- 220 ms top-left anchored animation: Tasks 4, 8, 11.
- Remember position but always start compact: Tasks 2, 8, 11.
- Favorites and recent eight: Tasks 2, 7, 8, 11.
- Recursive background index, exclusions, manual refresh: Tasks 3, 7, 8, 11.
- Search ranking and 30-result limit: Task 3.
- Single-click select, double-click Claude, Enter/Ctrl+Enter: Task 7.
- Current project, launch options, Terminal appearance: Tasks 5, 6, 7, 8.
- Window/tab behavior and explicit tab limitation: Tasks 6, 7, 10, 11.
- Appearance preview/apply/rollback: Tasks 5, 7, 8, 11.
- Corrupt config recovery and atomic writes: Task 2.
- Rotating diagnostic logs: Tasks 1, 9, 11.
- Session Monitor and exact HWND preservation: Tasks 6, 8, 11.
- Safe lifecycle and callback cancellation: Tasks 3, 4, 8, 11.
- Unit, integration, compilation, and Windows validation: Tasks 1-11.

### Placeholder scan

The implementation tasks contain no `TBD`, `TODO`, “implement later,” or unspecified error-handling steps. The verification template uses angle-bracket fields intentionally and explicitly requires replacing them with observed values before commit.

### Type consistency

The plan consistently uses:

- `LaunchOptions(terminal_mode, skip_permissions, hide_after_launch)`;
- `AppearanceSettings(mode, opacity)`;
- `LaunchResult(success, agent_type, terminal_mode, error)`;
- `DirectoryEntry(name, path, normalized_path, root_path, relative_path)`;
- `LauncherCallbacks` event names matching the design document;
- `WindowAnimator.animate_to(width, height, work_width, work_height, on_complete=None)`.
