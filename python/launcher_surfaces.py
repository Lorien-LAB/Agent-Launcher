from __future__ import annotations

from dataclasses import dataclass
import tkinter as tk

from launcher_geometry import stable_rounded_rectangle_points
from launcher_theme import interpolate_hex


@dataclass(frozen=True)
class GlassLayerSpec:
    shadow_bounds: tuple[int, int, int, int]
    panel_bounds: tuple[int, int, int, int]
    outer_radius: int


def _master_bg(master, fallback):
    try:
        return master.cget("bg")
    except (AttributeError, tk.TclError):
        return fallback


def _find_backdrop_host(master):
    current = master
    while current is not None:
        if hasattr(current, "register_surface") and hasattr(current, "unregister_surface"):
            return current
        current = getattr(current, "master", None)
    return None


def glass_content_inset(radius: int, padding: int) -> int:
    return max(int(padding), int(round(float(radius) * 0.45)))


def glass_layer_spec(width: int, height: int, radius: int) -> GlassLayerSpec:
    width = max(4, int(width))
    height = max(6, int(height))
    outer_radius = max(1, min(int(radius), width // 2 - 1, height // 2 - 1))
    return GlassLayerSpec(
        shadow_bounds=(2, 3, width - 2, height - 1),
        panel_bounds=(2, 2, width - 2, height - 2),
        outer_radius=outer_radius,
    )


class BackdropFrame(tk.Frame):
    def __init__(self, master, *, theme, **kwargs):
        self.theme = theme
        self._backdrop_host = _find_backdrop_host(master)
        super().__init__(master, bg=_master_bg(master, theme["window_bg"]), **kwargs)
        if self._backdrop_host is not None:
            self._backdrop_host.register_surface(self)

    def set_backdrop_color(self, color):
        color = str(color)
        self.configure(bg=color)
        for child in self.winfo_children():
            try:
                if hasattr(child, "set_backdrop_color"):
                    child.set_backdrop_color(color)
                else:
                    child.configure(bg=color)
            except (AttributeError, tk.TclError):
                pass

    def destroy(self):
        if self._backdrop_host is not None:
            try:
                self._backdrop_host.unregister_surface(self)
            except Exception:
                pass
            self._backdrop_host = None
        super().destroy()


class CleanRoundedCard(tk.Canvas):
    def __init__(self, master, *, theme, scale, radius=22, padding=12, **kwargs):
        self.theme = theme
        self.s = scale
        self.radius = max(1, int(radius))
        self.padding = max(0, int(padding))
        self.content_inset = glass_content_inset(self.radius, self.padding)
        self._hovered = False
        self._focused = False
        self._backdrop_host = _find_backdrop_host(master)
        self._backdrop_color = _master_bg(master, theme["window_bg"])
        super().__init__(master, bg=self._backdrop_color, highlightthickness=0, bd=0, **kwargs)
        self._shadow = self.create_polygon(
            *stable_rounded_rectangle_points(2, 3, 4, 5, 1),
            smooth=True,
            splinesteps=24,
            fill=theme["glass_shadow"],
            outline="",
        )
        self._shape = self.create_polygon(
            *stable_rounded_rectangle_points(2, 2, 4, 4, 1),
            smooth=True,
            splinesteps=24,
            fill=self._panel_fill(),
            outline=theme["glass_border"],
            width=self.s(1),
        )
        self.content = tk.Frame(self, bg=theme["glass_content"])
        inset = self.s(self.content_inset)
        self._content_window = self.create_window(inset, inset, anchor="nw", window=self.content)
        self.bind("<Configure>", self._on_configure)
        if self._backdrop_host is not None:
            self._backdrop_host.register_surface(self)

    def _panel_fill(self):
        target = self.theme["glass_fill_hover"] if self._hovered else self.theme["glass_fill"]
        return interpolate_hex(self._backdrop_color, target, 0.66)

    def set_backdrop_color(self, color):
        self._backdrop_color = str(color)
        self.configure(bg=self._backdrop_color)
        self.itemconfigure(self._shape, fill=self._panel_fill())

    def _on_configure(self, event):
        width = max(4, int(event.width))
        height = max(6, int(event.height))
        spec = glass_layer_spec(width, height, self.s(self.radius))
        self.coords(self._shadow, *stable_rounded_rectangle_points(*spec.shadow_bounds, spec.outer_radius))
        self.coords(self._shape, *stable_rounded_rectangle_points(*spec.panel_bounds, spec.outer_radius))
        inset = self.s(self.content_inset)
        self.coords(self._content_window, inset, inset)
        self.itemconfigure(self._content_window, width=max(1, width - inset * 2), height=max(1, height - inset * 2))

    def set_interactive_state(self, *, hovered=False, focused=False):
        self._hovered = bool(hovered)
        self._focused = bool(focused)
        border = self.theme["glass_border_bright"] if self._focused else self.theme["border_hover"] if self._hovered else self.theme["glass_border"]
        self.itemconfigure(self._shape, fill=self._panel_fill(), outline=border)

    def destroy(self):
        if self._backdrop_host is not None:
            try:
                self._backdrop_host.unregister_surface(self)
            except Exception:
                pass
            self._backdrop_host = None
        super().destroy()
