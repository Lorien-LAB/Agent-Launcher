from __future__ import annotations

import tkinter as tk

from launcher_widgets import scrollbar_should_show


def thumb_geometry(first, last, *, height, min_height=34, inset=3):
    height = max(1, int(height))
    inset = max(0, min(int(inset), height // 2))
    usable = max(1, height - inset * 2)
    first = max(0.0, min(1.0, float(first)))
    last = max(first, min(1.0, float(last)))
    top = inset + round(first * usable)
    bottom = inset + round(last * usable)
    minimum = min(usable, max(1, int(min_height)))
    if bottom - top < minimum:
        bottom = min(height - inset, top + minimum)
        top = max(inset, bottom - minimum)
    return top, bottom


def _master_bg(master, fallback):
    try:
        return master.cget("bg")
    except (AttributeError, tk.TclError):
        return fallback


class PillScrollbar(tk.Canvas):
    def __init__(self, master, *, command, theme, scale, on_visibility_change=None):
        self.command = command
        self.theme = theme
        self.s = scale
        self.on_visibility_change = on_visibility_change
        self.first = 0.0
        self.last = 1.0
        self._visible = False
        self._hovered = False
        self._drag_start_y = None
        self._drag_start_first = 0.0
        super().__init__(
            master,
            width=self.s(10),
            bg=_master_bg(master, theme["glass_content"]),
            highlightthickness=0,
            bd=0,
        )
        self._track = self.create_line(0, 0, 0, 0, capstyle=tk.ROUND, state="hidden")
        self._thumb = self.create_line(0, 0, 0, 0, capstyle=tk.ROUND, state="hidden")
        self.bind("<Configure>", lambda _event: self._render())
        self.bind("<Enter>", lambda _event: self._set_hovered(True))
        self.bind("<Leave>", lambda _event: self._set_hovered(False))
        self.bind("<ButtonPress-1>", self._press)
        self.bind("<B1-Motion>", self._drag)
        self.bind("<ButtonRelease-1>", lambda _event: self._release())

    def set(self, first, last):
        self.first = max(0.0, min(1.0, float(first)))
        self.last = max(self.first, min(1.0, float(last)))
        visible = scrollbar_should_show(self.first, self.last)
        changed = visible != self._visible
        self._visible = visible
        if changed and self.on_visibility_change is not None:
            self.on_visibility_change(visible)
        self._render()

    def visible(self):
        return self._visible

    def _thumb_bounds(self):
        return thumb_geometry(
            self.first,
            self.last,
            height=max(1, int(self.winfo_height())),
            min_height=self.s(32),
            inset=self.s(4),
        )

    def _set_hovered(self, hovered):
        self._hovered = bool(hovered)
        self.configure(cursor="hand2" if self._hovered else "arrow")
        self._render()

    def _render(self):
        if not self._visible:
            self.itemconfigure(self._track, state="hidden")
            self.itemconfigure(self._thumb, state="hidden")
            return
        width = max(2, int(self.winfo_width()))
        height = max(2, int(self.winfo_height()))
        center = width // 2
        top, bottom = self._thumb_bounds()
        self.coords(self._track, center, self.s(6), center, height - self.s(6))
        self.coords(self._thumb, center, top, center, bottom)
        self.itemconfigure(
            self._track,
            state="normal",
            fill=self.theme["border"] if self._hovered else self.theme["surface_2"],
            width=self.s(2),
        )
        self.itemconfigure(
            self._thumb,
            state="normal",
            fill=self.theme["border_hover"] if self._hovered else self.theme["glass_border"],
            width=self.s(7 if self._hovered else 5),
        )

    def _press(self, event):
        if not self._visible:
            return "break"
        top, bottom = self._thumb_bounds()
        if top <= int(event.y) <= bottom:
            self._drag_start_y = int(event.y)
            self._drag_start_first = self.first
        else:
            page = max(1e-9, self.last - self.first)
            fraction = int(event.y) / max(1, int(self.winfo_height()))
            self.command("moveto", max(0.0, min(1.0 - page, fraction - page / 2)))
        return "break"

    def _drag(self, event):
        if self._drag_start_y is None:
            return "break"
        height = max(1, int(self.winfo_height()))
        movable = max(0.0, 1.0 - (self.last - self.first))
        delta = (int(event.y) - self._drag_start_y) / height
        self.command("moveto", max(0.0, min(movable, self._drag_start_first + delta)))
        return "break"

    def _release(self):
        self._drag_start_y = None
        return "break"
