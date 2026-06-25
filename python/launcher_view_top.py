from __future__ import annotations

import tkinter as tk

from launcher_background import LauncherBackground
from launcher_directory_list import DirectoryList
from launcher_search_field import SearchField
from launcher_settings_panel import LauncherSettingsPanel
from launcher_titlebar import LauncherTitleBar
from launcher_widgets import GhostButton


def build_top(view) -> None:
    theme = view.theme
    view.background = LauncherBackground(view.root, theme=theme, scale=view.s)
    view.background.pack(fill="both", expand=True)
    view.container = view.background
    view.background.grid_rowconfigure(2, weight=1)
    view.background.grid_columnconfigure(0, weight=1)
    view.background.grid_columnconfigure(1, weight=0)

    view.titlebar = LauncherTitleBar(
        view.background,
        theme=theme,
        scale=view.s,
        on_minimize=view.on_minimize,
        on_toggle_maximize=view.on_toggle_maximize,
        on_close=view.on_close,
        on_toggle_expanded=view.callbacks.on_toggle_expanded,
        drag_controller=view.chrome_controller,
    )
    view.titlebar.grid(row=0, column=0, columnspan=2, sticky="ew")

    search_row = tk.Frame(view.background, bg=theme["window_bg"])
    search_row.grid(
        row=1,
        column=0,
        columnspan=2,
        sticky="ew",
        padx=view.s(12),
        pady=(view.s(10), view.s(8)),
    )
    search_row.grid_columnconfigure(0, weight=1)

    view.search_field = SearchField(
        search_row,
        variable=view.search_var,
        theme=theme,
        scale=view.s,
        placeholder="Search projects or directories…",
        on_submit=lambda: view._launch("claude"),
    )
    view.search_field.grid(row=0, column=0, sticky="ew")
    view.search_entry = view.search_field.entry

    view.refresh_button = GhostButton(
        search_row,
        text="↻",
        command=view.callbacks.on_refresh_index,
        theme=theme,
        scale=view.s,
        width=42,
        height=40,
    )
    view.refresh_button.grid(row=0, column=1, padx=(view.s(8), 0))

    view.directory_list = DirectoryList(
        view.background,
        theme=theme,
        scale=view.s,
        on_select=view.callbacks.on_select,
        on_launch=view.callbacks.on_launch,
        on_favorite=view.callbacks.on_toggle_favorite,
    )
    view.directory_list.grid(
        row=2,
        column=0,
        columnspan=2,
        sticky="nsew",
        padx=view.s(12),
    )

    view.settings_panel = LauncherSettingsPanel(
        view.background,
        theme=theme,
        scale=view.s,
        callbacks=view.callbacks,
    )
    view.settings_panel.grid_remove()
