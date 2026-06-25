from __future__ import annotations

import tkinter as tk

from launcher_chrome import LauncherChromeController
from launcher_settings_models import resolved_theme
from launcher_view_data import LauncherViewData
from launcher_view_footer import build_footer
from launcher_view_layout import LauncherViewLayout
from launcher_view_models import (
    COMPACT_SIZE,
    EXPANDED_SIZE,
    DirectoryRow,
    LauncherCallbacks,
    compose_home_rows,
    layout_spec,
    truncate_middle,
)
from launcher_view_status import build_status
from launcher_view_top import build_top


class LauncherView(LauncherViewData, LauncherViewLayout):
    def __init__(
        self,
        root,
        callbacks: LauncherCallbacks,
        colors: dict | None = None,
        scale=lambda value: value,
        *,
        theme: dict | None = None,
        chrome_controller: LauncherChromeController | None = None,
        on_minimize=None,
        on_toggle_maximize=None,
        on_close=None,
    ):
        self.root = root
        self.callbacks = callbacks
        self.theme = resolved_theme(theme, colors)
        self.colors = self.theme
        self.s = scale
        self.expanded = False
        self.selected_path = None
        self._destroyed = False
        self._transition_expanding = None

        self.chrome_controller = (
            chrome_controller or LauncherChromeController(root)
        )
        self.on_minimize = on_minimize or self.root.iconify
        self.on_toggle_maximize = on_toggle_maximize or (lambda: None)
        self.on_close = on_close or self.root.withdraw

        self.search_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="Ready")
        self.selected_var = tk.StringVar(value="No directory selected")

        build_top(self)
        build_footer(self)
        build_status(self)

        self._search_trace = self.search_var.trace_add(
            "write",
            self._search_changed,
        )
        self.root.bind(
            "<Return>",
            lambda _event: self._launch("claude"),
            add="+",
        )
        self.root.bind(
            "<Control-Return>",
            lambda _event: self._launch("hermes"),
            add="+",
        )
        self.root.bind(
            "<Up>",
            lambda _event: self._move_selection(-1),
            add="+",
        )
        self.root.bind(
            "<Down>",
            lambda _event: self._move_selection(1),
            add="+",
        )
        self.set_expanded(False)


__all__ = [
    "COMPACT_SIZE",
    "EXPANDED_SIZE",
    "DirectoryRow",
    "LauncherCallbacks",
    "LauncherView",
    "compose_home_rows",
    "layout_spec",
    "truncate_middle",
]
