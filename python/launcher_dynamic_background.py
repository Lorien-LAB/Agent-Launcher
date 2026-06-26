from __future__ import annotations

import math

from launcher_background import GlowSpec, LauncherBackground, blend_for_glow


def animate_glow(spec: GlowSpec, phase: float) -> GlowSpec:
    offset = 0.0 if spec.role == "purple" else 1.7
    return GlowSpec(
        spec.role,
        spec.center_x + round(math.sin(phase + offset) * 24),
        spec.center_y + round(math.cos(phase * 0.78 + offset) * 17),
        spec.radius + 18,
        spec.opacity * (1.16 + 0.08 * math.sin(phase * 0.62 + offset)),
    )


class DynamicLauncherBackground(LauncherBackground):
    def __init__(self, master, *, theme, scale):
        self._phase = 0.0
        self._motion_after = None
        super().__init__(master, theme=theme, scale=scale)
        self.bind("<Map>", lambda _event: self._schedule_motion(), add="+")
        self.bind("<Unmap>", lambda _event: self._cancel_motion(), add="+")
        self._schedule_motion()

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
        super().destroy()
