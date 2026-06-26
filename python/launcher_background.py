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
    """Return stronger ambient glow geometry in logical pixels."""
    width = max(1, int(width))
    height = max(1, int(height))
    glows = [
        GlowSpec(
            "purple",
            center_x=min(width, 92),
            center_y=min(height, 76),
            radius=min(250, max(180, width // 2)),
            opacity=0.24,
        )
    ]
    if expanded:
        glows.append(
            GlowSpec(
                "blue",
                center_x=round(width * 0.78),
                center_y=round(height * 0.34),
                radius=min(230, max(180, width // 4)),
                opacity=0.18,
            )
        )
    return glows


def blend_for_glow(background: str, glow: str, opacity: float) -> str:
    return interpolate_hex(
        background,
        glow,
        max(0.0, min(1.0, float(opacity))),
    )


class LauncherBackground(tk.Canvas):
    """Cached ambient gradient layer for compact and expanded layouts."""

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
        scale_factor = max(0.01, float(self.s(100)) / 100.0)
        logical_width = max(1, round(width / scale_factor))
        logical_height = max(1, round(height / scale_factor))
        self.delete("ambient_glow")
        for glow in glow_spec_for_mode(
            self.expanded,
            logical_width,
            logical_height,
        ):
            self._draw_glow(glow)
        self.tag_lower("ambient_glow")

    def _draw_glow(self, spec: GlowSpec) -> None:
        background = self.theme["window_bg"]
        accent = self.theme[spec.role]
        rings = 26
        center_x = self.s(spec.center_x)
        center_y = self.s(spec.center_y)
        # Draw widest/faintest rings first, strongest center last.
        for index in range(rings, 0, -1):
            fraction = index / rings
            radius = max(1, round(self.s(spec.radius) * fraction))
            strength = spec.opacity * (1.0 - 0.76 * fraction)
            color = blend_for_glow(background, accent, strength)
            self.create_oval(
                center_x - radius,
                center_y - radius,
                center_x + radius,
                center_y + radius,
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
