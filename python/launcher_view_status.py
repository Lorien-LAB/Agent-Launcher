from __future__ import annotations

import tkinter as tk


def build_status(view) -> None:
    theme = view.theme
    status_row = tk.Frame(view.background, bg=theme["window_bg"])
    status_row.grid(
        row=4,
        column=0,
        columnspan=2,
        sticky="ew",
        padx=view.s(14),
        pady=(view.s(6), view.s(8)),
    )
    status_row.grid_columnconfigure(1, weight=1)

    view.status_dot = tk.Label(
        status_row,
        text="●",
        bg=theme["window_bg"],
        fg=theme["text_muted"],
        font=("Segoe UI Symbol", 6),
    )
    view.status_dot.grid(row=0, column=0, padx=(0, view.s(6)))

    view.status_label = tk.Label(
        status_row,
        textvariable=view.status_var,
        bg=theme["window_bg"],
        fg=theme["text_muted"],
        anchor="w",
        font=("Segoe UI", 8),
    )
    view.status_label.grid(row=0, column=1, sticky="ew")
