from __future__ import annotations

from dataclasses import dataclass

from launcher_state import normalize_path
from launcher_theme import COMPACT_LOGICAL_SIZE, EXPANDED_LOGICAL_SIZE


COMPACT_SIZE = COMPACT_LOGICAL_SIZE
EXPANDED_SIZE = EXPANDED_LOGICAL_SIZE


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
    on_remove_recent: object = None


@dataclass(frozen=True)
class LayoutSpec:
    sections: tuple[str, ...]
    column_weights: tuple[int, int]
    show_settings: bool


def layout_spec(expanded: bool) -> LayoutSpec:
    return LayoutSpec(
        sections=(
            ("titlebar", "search", "directory_list", "settings", "status")
            if expanded
            else (
                "titlebar",
                "search",
                "directory_list",
                "compact_footer",
                "status",
            )
        ),
        column_weights=(45, 55),
        show_settings=bool(expanded),
    )


def compose_home_rows(favorites: list[str], recents: list[str]) -> list[DirectoryRow]:
    rows: list[DirectoryRow] = []
    seen: set[str] = set()
    for section, paths, favorite in (
        ("favorite", favorites, True),
        ("recent", recents, False),
    ):
        for path in paths:
            key = normalize_path(path)
            if not key or key in seen:
                continue
            seen.add(key)
            rows.append(DirectoryRow(section, path, favorite))
    return rows


def truncate_middle(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    if limit <= 1:
        return "…"[:limit]
    tail = max(1, limit * 2 // 3)
    head = max(1, limit - tail - 1)
    return f"{value[:head]}…{value[-tail:]}"
