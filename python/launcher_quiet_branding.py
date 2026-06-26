from __future__ import annotations

from dataclasses import replace
import math

from launcher_branding import GlassBrandButton, glass_palette
from launcher_theme import interpolate_hex


def quiet_brand_palette(theme: dict, role: str):
    base = glass_palette(theme, role)
    accent = theme[role]
    surface = theme["surface_1"]
    return replace(
        base,
        normal=interpolate_hex(surface, accent, 0.10),
        hover=interpolate_hex(surface, accent, 0.18),
        pressed=interpolate_hex(surface, accent, 0.26),
        border=theme["glass_border"],
        highlight=theme["glass_highlight"],
        shadow=interpolate_hex(theme["window_bg"], "#000000", 0.20),
    )


class QuietGlassBrandButton(GlassBrandButton):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.palette = quiet_brand_palette(self.theme, self.role)
        if hasattr(self, "_highlight"):
            self.itemconfigure(self._highlight, state="hidden")
        self._render()

    def _position_brand(self, center_x: int, center_y: int):
        if self.spec.icon_kind != "claude_burst":
            return super()._position_brand(center_x, center_y)
        lengths = (7, 6, 8, 6, 7, 5, 8, 6, 7, 6, 8, 6)
        inner = self.s(2)
        for index, (item, length) in enumerate(zip(self._brand_items, lengths)):
            angle = math.radians(index * 30 - 90)
            x1 = center_x + math.cos(angle) * inner
            y1 = center_y + math.sin(angle) * inner
            outer = self.s(length)
            x2 = center_x + math.cos(angle) * outer
            y2 = center_y + math.sin(angle) * outer
            self.coords(item, x1, y1, x2, y2)
