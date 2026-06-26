from __future__ import annotations

import math

from launcher_background import GlowSpec


def animate_glow(spec: GlowSpec, phase: float) -> GlowSpec:
    offset = 0.0 if spec.role == "purple" else 1.7
    return GlowSpec(
        spec.role,
        spec.center_x + round(math.sin(phase + offset) * 24),
        spec.center_y + round(math.cos(phase * 0.78 + offset) * 17),
        spec.radius,
        spec.opacity * (0.98 + 0.08 * math.sin(phase * 0.62 + offset)),
    )
