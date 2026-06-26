from __future__ import annotations

import tkinter as tk


def build_status(view) -> None:
    """Keep status state available to the coordinator without rendering a footer."""
    theme = view.theme
    view.status_row = tk.Frame(view.background, bg=theme["window_bg"])
    view.status_dot = tk.Label(
        view.status_row,
        text="●",
        bg=theme["window_bg"],
        fg=theme["text_muted"],
        font=("Segoe UI Symbol", 6),
    )
    view.status_label = tk.Label(
        view.status_row,
        textvariable=view.status_var,
        bg=theme["window_bg"],
        fg=theme["text_muted"],
        anchor="w",
        font=("Segoe UI", 8),
    )
    # Deliberately do not grid the status row. Indexing and transient messages
    # remain available programmatically, but no longer occupy visual space.
