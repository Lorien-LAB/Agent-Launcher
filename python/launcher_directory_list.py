from __future__ import annotations

import tkinter as tk

from launcher_directory_row import DirectoryRowWidget
from launcher_state import normalize_path
from launcher_theme import COLORS, METRICS
from launcher_widgets import OverlayScrollbar, RoundedCard


def section_title(section: str) -> str:
    return {
        "favorite": "FAVORITES",
        "recent": "RECENT",
        "search": "SEARCH RESULTS",
    }.get(section, str(section).upper())


def _resolved_theme(theme=None, colors=None):
    provided = theme if theme is not None else colors or {}
    resolved = dict(COLORS)
    legacy = {
        "base": "window_bg",
        "card": "surface_1",
        "list": "surface_1",
        "selected": "surface_selected",
        "text": "text_primary",
        "sub": "text_secondary",
        "muted": "text_muted",
        "accent": "purple",
        "green": "claude",
        "orange": "hermes",
        "error": "danger",
    }
    for key, value in provided.items():
        if key in resolved:
            resolved[key] = value
    for old, new in legacy.items():
        if old in provided and new not in provided:
            resolved[new] = provided[old]
    return resolved


class DirectoryList(RoundedCard):
    def __init__(
        self,
        master,
        colors=None,
        scale=lambda value: value,
        on_select=None,
        on_launch=None,
        on_favorite=None,
        *,
        theme=None,
    ):
        self.theme = _resolved_theme(theme, colors)
        self.s = scale
        self.on_select = on_select or (lambda _path: None)
        self.on_launch = on_launch or (lambda _agent: None)
        self.on_favorite = on_favorite or (lambda _path: None)
        self.rows = []
        self.selected_path = None
        self.row_widgets = {}
        super().__init__(
            master,
            theme=self.theme,
            scale=self.s,
            radius=METRICS.card_radius,
            padding=6,
        )

        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)
        self.canvas = tk.Canvas(
            self.content,
            bg=self.theme["surface_1"],
            highlightthickness=0,
            bd=0,
            yscrollincrement=self.s(METRICS.directory_row_height),
        )
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar = OverlayScrollbar(
            self.content,
            command=self.canvas.yview,
            theme=self.theme,
            scale=self.s,
            on_visibility_change=self._set_scrollbar_visible,
        )
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.scrollbar.grid_remove()
        self.canvas.configure(yscrollcommand=self._on_yview)

        self.body = tk.Frame(self.canvas, bg=self.theme["surface_1"])
        self.body_window = self.canvas.create_window(
            (0, 0),
            window=self.body,
            anchor="nw",
        )
        self.body.bind("<Configure>", self._body_configured)
        self.canvas.bind("<Configure>", self._canvas_configured)
        self._bind_wheel(self.canvas)
        self._bind_wheel(self.body)

    def _set_scrollbar_visible(self, visible):
        if visible:
            self.scrollbar.grid()
        else:
            self.scrollbar.grid_remove()

    def _on_yview(self, first, last):
        self.scrollbar.set(first, last)

    def _body_configured(self, _event=None):
        bbox = self.canvas.bbox("all")
        if bbox is not None:
            self.canvas.configure(scrollregion=bbox)

    def _canvas_configured(self, event):
        self.canvas.itemconfigure(self.body_window, width=max(1, int(event.width)))

    def _bind_wheel(self, widget):
        widget.bind("<MouseWheel>", self._mousewheel, add="+")

    def _mousewheel(self, event):
        delta = -1 if int(event.delta) > 0 else 1
        self.canvas.yview_scroll(delta, "units")
        return "break"

    def render(self, rows):
        fraction = self.scroll_fraction()
        for child in self.body.winfo_children():
            child.destroy()
        self.rows = list(rows)
        self.row_widgets = {}
        current_section = None
        selected_key = normalize_path(self.selected_path or "")

        for row in self.rows:
            if row.section != current_section:
                current_section = row.section
                heading = tk.Label(
                    self.body,
                    text=section_title(current_section),
                    bg=self.theme["surface_1"],
                    fg=self.theme["text_muted"],
                    anchor="w",
                    font=("Segoe UI Semibold", 8),
                )
                heading.pack(
                    fill="x",
                    padx=self.s(8),
                    pady=(self.s(8), self.s(3)),
                )
                self._bind_wheel(heading)

            widget = DirectoryRowWidget(
                self.body,
                row,
                theme=self.theme,
                scale=self.s,
                on_select=self.on_select,
                on_launch=self.on_launch,
                on_favorite=self.on_favorite,
            )
            widget.pack(
                fill="x",
                padx=self.s(3),
                pady=self.s(1),
            )
            self._bind_wheel(widget)
            key = normalize_path(row.path)
            widget.set_selected(key == selected_key)
            self.row_widgets[key] = widget

        if not self.rows:
            empty = tk.Label(
                self.body,
                text="No matching directories",
                bg=self.theme["surface_1"],
                fg=self.theme["text_muted"],
                pady=self.s(24),
                font=("Segoe UI", 9),
            )
            empty.pack(fill="x")
            self._bind_wheel(empty)

        self.body.update_idletasks()
        self._body_configured()
        self.restore_scroll(fraction)

    def set_selected(self, path):
        self.selected_path = path
        selected_key = normalize_path(path or "")
        for key, widget in self.row_widgets.items():
            widget.set_selected(key == selected_key)

    def move_selection(self, delta):
        if not self.rows:
            return None
        selected_key = normalize_path(self.selected_path or "")
        keys = [normalize_path(row.path) for row in self.rows]
        try:
            index = keys.index(selected_key)
        except ValueError:
            index = -1 if delta > 0 else 0
        index = max(0, min(len(self.rows) - 1, index + int(delta)))
        return self.rows[index].path

    def scroll_fraction(self):
        try:
            return float(self.canvas.yview()[0])
        except (IndexError, tk.TclError, ValueError):
            return 0.0

    def restore_scroll(self, fraction):
        try:
            self.canvas.yview_moveto(max(0.0, min(1.0, float(fraction))))
        except (tk.TclError, ValueError):
            pass
