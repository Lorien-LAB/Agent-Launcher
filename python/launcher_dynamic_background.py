from __future__ import annotations

import math
import weakref

from launcher_background import (
    GlowSpec,
    LauncherBackground,
    blend_for_glow,
    glow_spec_for_mode,
)


def animate_glow(spec: GlowSpec, phase: float) -> GlowSpec:
    offset = 0.0 if spec.role == "purple" else 1.7
    return GlowSpec(
        spec.role,
        spec.center_x + round(math.sin(phase + offset) * 24),
        spec.center_y + round(math.cos(phase * 0.78 + offset) * 17),
        spec.radius + 18,
        spec.opacity * (1.16 + 0.08 * math.sin(phase * 0.62 + offset)),
    )


def sample_glow_color(background: str, theme: dict, glows, x: float, y: float) -> str:
    """Approximate the opaque radial-ring color drawn at one logical point."""
    color = background
    for spec in glows:
        distance = math.hypot(float(x) - spec.center_x, float(y) - spec.center_y)
        if distance > spec.radius:
            continue
        fraction = max(1.0 / 28.0, distance / max(1.0, float(spec.radius)))
        strength = spec.opacity * (1.0 - 0.72 * fraction)
        color = blend_for_glow(background, theme[spec.role], strength)
    return color


class DynamicLauncherBackground(LauncherBackground):
    def __init__(self, master, *, theme, scale):
        self._phase = 0.0
        self._motion_after = None
        self._surface_refs = []
        super().__init__(master, theme=theme, scale=scale)
        self.bind("<Map>", lambda _event: self._schedule_motion(), add="+")
        self.bind("<Unmap>", lambda _event: self._cancel_motion(), add="+")
        self._schedule_motion()

    def register_surface(self, widget):
        for reference in self._surface_refs:
            if reference() is widget:
                return
        self._surface_refs.append(weakref.ref(widget))
        self.after_idle(self._update_surface_backdrops)

    def unregister_surface(self, widget):
        self._surface_refs = [
            reference
            for reference in self._surface_refs
            if reference() is not None and reference() is not widget
        ]

    def _reduced_motion(self):
        try:
            return bool(getattr(self.winfo_toplevel(), "_launcher_reduced_motion", False))
        except Exception:
            return True

    def _schedule_motion(self):
        if self._motion_after is None and not self._reduced_motion():
            self._motion_after = self.after(140, self._motion_step)

    def _cancel_motion(self):
        if self._motion_after is not None:
            try:
                self.after_cancel(self._motion_after)
            except Exception:
                pass
            self._motion_after = None

    def _motion_step(self):
        self._motion_after = None
        if self._reduced_motion():
            return
        self._phase += 0.055
        self.redraw(force=True)
        self._schedule_motion()

    def _logical_size(self):
        factor = max(0.01, float(self.s(100)) / 100.0)
        return (
            max(1, round(max(1, int(self.winfo_width())) / factor)),
            max(1, round(max(1, int(self.winfo_height())) / factor)),
            factor,
        )

    def _animated_glows(self):
        width, height, _factor = self._logical_size()
        return [
            animate_glow(spec, self._phase)
            for spec in glow_spec_for_mode(self.expanded, width, height)
        ]

    def redraw(self, force=False):
        super().redraw(force=force)
        self._update_surface_backdrops()

    def _update_surface_backdrops(self):
        if not self.winfo_exists():
            return
        glows = self._animated_glows()
        _width, _height, factor = self._logical_size()
        try:
            origin_x = self.winfo_rootx()
            origin_y = self.winfo_rooty()
        except Exception:
            return
        live_refs = []
        for reference in self._surface_refs:
            widget = reference()
            if widget is None:
                continue
            try:
                if not widget.winfo_exists():
                    continue
                center_x = widget.winfo_rootx() - origin_x + widget.winfo_width() / 2
                center_y = widget.winfo_rooty() - origin_y + widget.winfo_height() / 2
                color = sample_glow_color(
                    self.theme["window_bg"],
                    self.theme,
                    glows,
                    center_x / factor,
                    center_y / factor,
                )
                if hasattr(widget, "set_backdrop_color"):
                    widget.set_backdrop_color(color)
                else:
                    widget.configure(bg=color)
                live_refs.append(reference)
            except Exception:
                continue
        self._surface_refs = live_refs

    def _draw_glow(self, spec):
        spec = animate_glow(spec, self._phase)
        background = self.theme["window_bg"]
        accent = self.theme[spec.role]
        rings = 28
        center_x = self.s(spec.center_x)
        center_y = self.s(spec.center_y)
        for index in range(rings, 0, -1):
            fraction = index / rings
            radius = max(1, round(self.s(spec.radius) * fraction))
            strength = spec.opacity * (1.0 - 0.72 * fraction)
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
        self._cancel_motion()
        self._surface_refs = []
        super().destroy()
