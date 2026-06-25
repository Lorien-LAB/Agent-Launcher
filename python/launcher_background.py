from __future__ import annotations

from dataclasses import dataclass
import tkinter as tk

from launcher_theme import interpolate_hex


@dataclass(frozen=True)
class GlowSpec:
    role: str
    center_x: int
    center_y: int
    radius: int
    opacity: float


def glow_spec_for_mode(expanded: bool, width: int, height: int) -> list[GlowSpec]:
    width = max(1, int(width))
    height = max(1, int(height))
    glows = [
        GlowSpec(
            "purple",
            center_x=min(width, 72),
            center_y=min(height, 52),
            radius=min(180, max(140, width // 3)),
            opacity=0.14,
        )
    ]
    if expanded:
        glows.append(
            GlowSpec(
                "blue",
                center_x=round(width * 0.72),
                center_y=round(height * 0.28),
                radius=min(160, max(120, width // 5)),
                opacity=0.10,
            )
        )
    return glows


def blend_for_glow(background: str, glow: str, opacity: float) -> str:
    return interpolate_hex(background, glow, max(0.0, min(1.0, float(opacity))))


class LauncherBackground(tk.Canvas):
    """Low-cost cached ambient glow layer for compact and expanded layouts."""

    def __init__(self, master, *, theme, scale):
        self.theme = theme
        self.s = scale
        self.expanded = False
        self._redraw_after = None
        self._last_render_key = None
        super().__init__(
            master,
            bg=theme["window_bg"],
            highlightthickness=0,
            bd=0,
        )
        self.bind("<Configure>", self._schedule_redraw)

    def set_expanded(self, expanded: bool) -> None:
        expanded = bool(expanded)
        if expanded == self.expanded:
            return
        self.expanded = expanded
        self.redraw(force=True)

    def _schedule_redraw(self, _event=None) -> None:
        if self._redraw_after is not None:
            try:
                self.after_cancel(self._redraw_after)
            except tk.TclError:
                pass
        self._redraw_after = self.after(80, self.redraw)

    def redraw(self, force=False) -> None:
        self._redraw_after = None
        width = max(1, int(self.winfo_width()))
        height = max(1, int(self.winfo_height()))
        render_key = (self.expanded, width, height)
        if not force and render_key == self._last_render_key:
            return
        self._last_render_key = render_key
        self.delete("ambient_glow")
        for glow in glow_spec_for_mode(self.expanded, width, height):
            self._draw_glow(glow)
        self.tag_lower("ambient_glow")

    def _draw_glow(self, spec: GlowSpec) -> None:
        background = self.theme["window_bg"]
        accent = self.theme[spec.role]
        rings = 18
        # Draw the widest, faintest rings first so the center remains strongest.
        for index in range(rings, 0, -1):
            fraction = index / rings
            radius = max(1, round(self.s(spec.radius) * fraction))
            strength = spec.opacity * (1.0 - 0.84 * fraction)
            color = blend_for_glow(background, accent, strength)
            self.create_oval(
                self.s(spec.center_x) - radius,
                self.s(spec.center_y) - radius,
                self.s(spec.center_x) + radius,
                self.s(spec.center_y) + radius,
                fill=color,
                outline="",
                tags=("ambient_glow",),
            )

    def destroy(self):
        if self._redraw_after is not None:
            try:
                self.after_cancel(self._redraw_after)
            except tk.TclError:
                pass
            self._redraw_after = None
        super().destroy()
