from __future__ import annotations

from dataclasses import dataclass
import os

from launcher_theme import COLORS


@dataclass(frozen=True)
class ProjectSummary:
    name: str
    path: str
    actions_enabled: bool


def project_summary(path):
    if not path:
        return ProjectSummary("No project selected", "Choose a project from the list", False)
    return ProjectSummary(os.path.basename(path.rstrip("\\/")) or path, path, True)


def appearance_status_text(dirty: bool, applied_now: bool) -> str:
    if dirty:
        return "Previewing"
    if applied_now:
        return "Applied"
    return "No changes"


def resolved_theme(theme=None, colors=None):
    provided = theme if theme is not None else colors or {}
    resolved = dict(COLORS)
    legacy = {"base": "window_bg", "card": "surface_1", "list": "surface_1", "selected": "surface_selected", "text": "text_primary", "sub": "text_secondary", "muted": "text_muted", "accent": "purple", "green": "claude", "orange": "hermes", "error": "danger"}
    for key, value in provided.items():
        if key in resolved:
            resolved[key] = value
    for old, new in legacy.items():
        if old in provided and new not in provided:
            resolved[new] = provided[old]
    return resolved
