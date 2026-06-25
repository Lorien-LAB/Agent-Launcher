from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WindowBounds:
    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True)
class DragAnchor:
    pointer_x: int
    pointer_y: int
    window_x: int
    window_y: int


class ChromeState:
    """Track maximized state and the bounds needed to restore a frameless window."""

    def __init__(self) -> None:
        self.maximized = False
        self.restore_bounds: WindowBounds | None = None

    def mark_maximized(self, restore_bounds: WindowBounds) -> None:
        self.restore_bounds = restore_bounds
        self.maximized = True

    def mark_restored(self) -> None:
        self.maximized = False


def calculate_drag_position(
    anchor: DragAnchor,
    pointer_x: int,
    pointer_y: int,
) -> tuple[int, int]:
    """Return a new top-left position while preserving the initial pointer offset."""
    return (
        anchor.window_x + int(pointer_x) - anchor.pointer_x,
        anchor.window_y + int(pointer_y) - anchor.pointer_y,
    )


def restore_for_drag(
    pointer_x: int,
    pointer_y: int,
    maximized: WindowBounds,
    restored: WindowBounds,
) -> WindowBounds:
    """Restore a maximized window under the pointer without a horizontal jump."""
    ratio = max(
        0.0,
        min(
            1.0,
            (int(pointer_x) - maximized.x) / max(1, maximized.width),
        ),
    )
    x = round(int(pointer_x) - restored.width * ratio)
    return WindowBounds(
        x=x,
        y=int(pointer_y),
        width=restored.width,
        height=restored.height,
    )
