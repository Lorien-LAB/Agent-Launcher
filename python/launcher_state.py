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
        opacity = int(self.opacity)
        if not 0 <= opacity <= 100:
            raise ValueError("opacity must be between 0 and 100")
        object.__setattr__(self, "opacity", opacity)


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
    """Return a stable Windows-friendly comparison key on every platform."""
    return os.path.normpath(path or "").replace("\\", "/").casefold()


def _is_network_path(path: str) -> bool:
    normalized = str(path).replace("/", "\\")
    return normalized.startswith("\\\\")


def _should_keep_path(path: str) -> bool:
    return os.path.isdir(path) or _is_network_path(path)


def _deduplicate_existing(paths: list[str], limit: int | None = None) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for raw in paths:
        value = str(raw)
        normalized = normalize_path(value)
        if not normalized or normalized in seen:
            continue
        if not _should_keep_path(value):
            continue
        seen.add(normalized)
        output.append(value)
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
        except (json.JSONDecodeError, OSError, TypeError, ValueError) as exc:
            self._backup_corrupt_file()
            self.state = LauncherState()
            self.recovered_corrupt_file = True
            if self.logger:
                self.logger.warning("launcher state reset after load failure: %s", exc)
        return self.state

    def _from_payload(self, payload: dict) -> LauncherState:
        if not isinstance(payload, dict):
            raise TypeError("launcher state must be an object")
        if int(payload.get("version", 0)) != STATE_VERSION:
            raise ValueError("unsupported state version")
        window = payload.get("window", {})
        if not isinstance(window, dict):
            raise TypeError("window state must be an object")
        options_payload = payload.get("launch_options", {})
        appearance_payload = payload.get("appearance", {})
        if not isinstance(options_payload, dict) or not isinstance(appearance_payload, dict):
            raise TypeError("launcher option state must be an object")
        options = LaunchOptions(**options_payload)
        appearance = AppearanceSettings(**appearance_payload)
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
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        backup = self.path.with_name(f"launcher-state.corrupt-{stamp}.json")
        self.path.replace(backup)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        payload = {
            "version": STATE_VERSION,
            "window": {"x": self.state.window_x, "y": self.state.window_y},
            "favorites": list(self.state.favorites),
            "recent_directories": list(self.state.recent_directories),
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
        if not normalized:
            raise FileNotFoundError(path)
        if any(normalize_path(item) == normalized for item in self.state.favorites):
            self.state.favorites = [
                item for item in self.state.favorites
                if normalize_path(item) != normalized
            ]
            self.save()
            return False
        if not _should_keep_path(path):
            raise FileNotFoundError(path)
        self.state.favorites.append(str(path))
        self.save()
        return True

    def record_recent(self, path: str) -> None:
        if not _should_keep_path(path):
            raise FileNotFoundError(path)
        normalized = normalize_path(path)
        remaining = [
            item for item in self.state.recent_directories
            if normalize_path(item) != normalized
        ]
        self.state.recent_directories = [str(path), *remaining][:8]
        self.save()

    def remove_recent(self, path: str) -> bool:
        normalized = normalize_path(path)
        if not normalized:
            return False
        previous = list(self.state.recent_directories)
        self.state.recent_directories = [
            item for item in previous if normalize_path(item) != normalized
        ]
        changed = self.state.recent_directories != previous
        if changed:
            self.save()
        return changed

    def update_window_position(self, x: int, y: int) -> None:
        self.state.window_x = int(x)
        self.state.window_y = int(y)

    def update_launch_options(self, options: LaunchOptions) -> None:
        self.state.launch_options = options
        self.save()

    def update_appearance(self, settings: AppearanceSettings) -> None:
        self.state.appearance = settings
        self.save()
