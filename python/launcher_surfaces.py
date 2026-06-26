from __future__ import annotations

import tkinter as tk

from launcher_geometry import stable_rounded_rectangle_points


def _master_bg(master, fallback):
    try:
        return master.cget("bg")
    except (AttributeError, tk.TclError):
        return fallback


class CleanRoundedCard(tk.Canvas):
    def __init__(self, master, *, theme, scale, radius=18, padding=12, **kwargs):
        self.theme = theme
        self.s = scale
        self.radius = radius
        self.padding = padding
        self._hovered = False
        self._focused = False
        super().__init__(
            master,
            bg=_master_bg(master, theme["window_bg"]),
            highlightthickness=0,
            bd=0,
            **kwargs,
        )
        self._shape = self.create_polygon(
            *stable_rounded_rectangle_points(1, 1, 3, 3, 1),
            smooth=True,
            splinesteps=24,
            fill=theme["surface_1"],
            outline=theme["border"],
            width=self.s(1),
        )
        self.content = tk.Frame(self, bg=theme["surface_1"])
        self._content_window = self.create_window(
            self.s(padding),
            self.s(padding),
            anchor="nw",
            window=self.content,
        )
        self.bind("<Configure>", self._on_configure)

    def _on_configure(self, event):
        width = max(2, int(event.width))
        height = max(2, int(event.height))
        inset = self.s(1)
        self.coords(
            self._shape,
            *stable_rounded_rectangle_points(
                inset,
                inset,
                width - inset,
                height - inset,
                self.s(self.radius),
            ),
        )
        self.itemconfigure(
            self._content_window,
            width=max(1, width - self.s(self.padding * 2)),
            height=max(1, height - self.s(self.padding * 2)),
        )

    def set_interactive_state(self, *, hovered=False, focused=False):
        self._hovered = bool(hovered)
        self._focused = bool(focused)
        background = self.theme["surface_hover"] if self._hovered else self.theme["surface_1"]
        border = (
            self.theme["border_focus"]
            if self._focused
            else self.theme["border_hover"] if self._hovered else self.theme["border"]
        )
        self.itemconfigure(self._shape, fill=background, outline=border)
        self.content.configure(bg=background)
