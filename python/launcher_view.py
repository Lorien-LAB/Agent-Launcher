from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from launcher_directory_list import DirectoryList
from launcher_state import normalize_path
from launcher_settings_panel import LauncherSettingsPanel
from launcher_view_models import (
    COMPACT_SIZE,
    EXPANDED_SIZE,
    DirectoryRow,
    LauncherCallbacks,
    compose_home_rows,
    truncate_middle,
)


class LauncherView:
    def __init__(self, root, callbacks: LauncherCallbacks, colors: dict, scale=lambda value: value):
        self.root = root
        self.callbacks = callbacks
        self.colors = colors
        self.s = scale
        self.expanded = False
        self.selected_path = None
        self._destroyed = False

        self.search_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="Ready")
        self.selected_var = tk.StringVar(value="No directory selected")

        self._build()
        self.search_var.trace_add("write", self._search_changed)
        self.root.bind("<Return>", lambda _event: self._launch("claude"), add="+")
        self.root.bind("<Control-Return>", lambda _event: self._launch("hermes"), add="+")
        self.root.bind("<Up>", lambda _event: self._move_selection(-1), add="+")
        self.root.bind("<Down>", lambda _event: self._move_selection(1), add="+")

    def _build(self):
        c = self.colors
        self.container = tk.Frame(self.root, bg=c["base"])
        self.container.pack(fill="both", expand=True, padx=self.s(8), pady=self.s(8))
        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_columnconfigure(1, weight=1)
        self.container.grid_rowconfigure(2, weight=1)

        header = tk.Frame(self.container, bg=c["base"])
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        tk.Label(
            header,
            text="Agent Launcher",
            bg=c["base"],
            fg=c["text"],
            font=("Segoe UI", 13, "bold"),
        ).pack(side="left")
        self.mode_button = tk.Button(
            header,
            text="Expand",
            command=self.callbacks.on_toggle_expanded,
            bg=c["card"],
            fg=c["text"],
            relief="flat",
        )
        self.mode_button.pack(side="right")
        self.refresh_button = tk.Button(
            header,
            text="Refresh",
            command=self.callbacks.on_refresh_index,
            bg=c["card"],
            fg=c["sub"],
            relief="flat",
        )
        self.refresh_button.pack(side="right", padx=(0, self.s(6)))

        self.search_entry = ttk.Entry(self.container, textvariable=self.search_var)
        self.search_entry.grid(
            row=1,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(self.s(8), self.s(6)),
        )

        self.directory_list = DirectoryList(
            self.container,
            colors=c,
            scale=self.s,
            on_select=self.callbacks.on_select,
            on_launch=self.callbacks.on_launch,
            on_favorite=self.callbacks.on_toggle_favorite,
        )
        self.directory_list.grid(row=2, column=0, sticky="nsew")

        self.settings_panel = LauncherSettingsPanel(
            self.container,
            colors=c,
            scale=self.s,
            callbacks=self.callbacks,
        )

        footer = tk.Frame(self.container, bg=c["base"])
        footer.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(self.s(6), 0))
        tk.Label(
            footer,
            textvariable=self.selected_var,
            bg=c["base"],
            fg=c["sub"],
            anchor="w",
            font=("Segoe UI", 8),
        ).pack(fill="x")
        buttons = tk.Frame(footer, bg=c["base"])
        buttons.pack(fill="x", pady=(self.s(4), 0))
        buttons.grid_columnconfigure(0, weight=1, uniform="launch")
        buttons.grid_columnconfigure(1, weight=1, uniform="launch")
        tk.Button(
            buttons,
            text="Claude Code",
            command=lambda: self._launch("claude"),
            bg=c["green"],
            relief="flat",
            font=("Segoe UI", 10, "bold"),
        ).grid(row=0, column=0, sticky="ew", padx=(0, self.s(4)))
        tk.Button(
            buttons,
            text="Hermes",
            command=lambda: self._launch("hermes"),
            bg=c["orange"],
            relief="flat",
            font=("Segoe UI", 10, "bold"),
        ).grid(row=0, column=1, sticky="ew")
        self.status_label = tk.Label(
            footer,
            textvariable=self.status_var,
            bg=c["base"],
            fg=c["muted"],
            anchor="w",
            font=("Segoe UI", 8),
        )
        self.status_label.pack(fill="x", pady=(self.s(4), 0))

    def _search_changed(self, *_args):
        if not self._destroyed:
            self.callbacks.on_search(self.search_var.get())

    def _launch(self, agent_type):
        self.callbacks.on_launch(agent_type)
        return "break"

    def _move_selection(self, delta):
        path = self.directory_list.move_selection(delta)
        if path:
            self.callbacks.on_select(path)
        return "break"

    def render_home(self, favorites, recents):
        self.directory_list.render(compose_home_rows(favorites, recents))

    def render_search_results(self, paths, favorites):
        rows = [
            DirectoryRow("search", path, normalize_path(path) in favorites)
            for path in paths
        ]
        self.directory_list.render(rows)

    def set_selected_path(self, path):
        self.selected_path = path
        shown = truncate_middle(path or "No directory selected", 56)
        self.selected_var.set(f"Current: {shown}" if path else shown)
        self.directory_list.set_selected(path)
        self.settings_panel.set_project(path)

    def set_status(self, message, error=False):
        self.status_var.set(message)
        self.status_label.configure(
            fg=self.colors["error"] if error else self.colors["muted"]
        )

    def set_indexing(self, active):
        self.refresh_button.configure(state="disabled" if active else "normal")

    def set_expanded(self, expanded):
        self.expanded = bool(expanded)
        if self.expanded:
            self.settings_panel.grid(
                row=2,
                column=1,
                sticky="nsew",
                padx=(self.s(8), 0),
            )
            self.mode_button.configure(text="Collapse")
        else:
            self.settings_panel.grid_remove()
            self.mode_button.configure(text="Expand")

    def set_launch_options(self, options):
        self.settings_panel.set_launch_options(options)

    def set_appearance(self, settings):
        self.settings_panel.set_appearance(settings)

    def get_scroll_fraction(self):
        return self.directory_list.scroll_fraction()

    def restore_scroll_fraction(self, fraction):
        self.directory_list.restore_scroll(fraction)

    def destroy(self):
        if self._destroyed:
            return
        self._destroyed = True
        try:
            self.container.destroy()
        except tk.TclError:
            pass


__all__ = [
    "COMPACT_SIZE",
    "EXPANDED_SIZE",
    "DirectoryRow",
    "LauncherCallbacks",
    "LauncherView",
    "compose_home_rows",
    "truncate_middle",
]
