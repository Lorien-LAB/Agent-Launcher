from __future__ import annotations

import tkinter as tk

from launcher_directory_row import DirectoryRowWidget
from launcher_state import normalize_path


class DirectoryList(tk.Frame):
    def __init__(self, master, colors, scale, on_select, on_launch, on_favorite):
        super().__init__(master, bg=colors["list"])
        self.colors = colors
        self.s = scale
        self.on_select = on_select
        self.on_launch = on_launch
        self.on_favorite = on_favorite
        self.rows = []
        self.selected_path = None
        self.row_widgets = {}

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.canvas = tk.Canvas(
            self,
            bg=colors["list"],
            highlightthickness=0,
            bd=0,
            yscrollincrement=self.s(28),
        )
        self.canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.body = tk.Frame(self.canvas, bg=colors["list"])
        self.body_window = self.canvas.create_window((0, 0), window=self.body, anchor="nw")
        self.body.bind(
            "<Configure>",
            lambda _event: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.canvas.bind(
            "<Configure>",
            lambda event: self.canvas.itemconfigure(self.body_window, width=event.width),
        )
        self.canvas.bind("<MouseWheel>", self._mousewheel)

    def _mousewheel(self, event):
        self.canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")
        return "break"

    def render(self, rows):
        fraction = self.scroll_fraction()
        for child in self.body.winfo_children():
            child.destroy()
        self.rows = list(rows)
        self.row_widgets = {}
        section = None
        for row in rows:
            if row.section != section:
                section = row.section
                title = {
                    "favorite": "Favorites",
                    "recent": "Recent",
                    "search": "Search Results",
                }.get(section, section.title())
                tk.Label(
                    self.body,
                    text=title,
                    bg=self.colors["list"],
                    fg=self.colors["muted"],
                    anchor="w",
                    font=("Segoe UI", 8, "bold"),
                ).pack(fill="x", padx=8, pady=(6, 2))
            widget = DirectoryRowWidget(
                self.body,
                row,
                self.colors,
                self.on_select,
                self.on_launch,
                self.on_favorite,
            )
            widget.pack(fill="x", padx=4, pady=1)
            key = normalize_path(row.path)
            widget.set_selected(key == normalize_path(self.selected_path or ""))
            self.row_widgets[key] = widget
        if not rows:
            tk.Label(
                self.body,
                text="No matching directories",
                bg=self.colors["list"],
                fg=self.colors["muted"],
                pady=18,
            ).pack(fill="x")
        self.body.update_idletasks()
        self.restore_scroll(fraction)

    def set_selected(self, path):
        self.selected_path = path
        selected_key = normalize_path(path or "")
        for key, widget in self.row_widgets.items():
            widget.set_selected(key == selected_key)

    def move_selection(self, delta):
        if not self.rows:
            return None
        paths = [row.path for row in self.rows]
        try:
            index = paths.index(self.selected_path)
        except ValueError:
            index = -1 if delta > 0 else 0
        index = max(0, min(len(paths) - 1, index + delta))
        return paths[index]

    def scroll_fraction(self):
        try:
            return float(self.canvas.yview()[0])
        except (IndexError, tk.TclError):
            return 0.0

    def restore_scroll(self, fraction):
        try:
            self.canvas.yview_moveto(max(0.0, min(1.0, float(fraction))))
        except tk.TclError:
            pass
