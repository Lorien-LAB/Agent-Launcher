from __future__ import annotations

import tkinter as tk

from launcher_branding import GlassBrandButton
from launcher_widgets import RoundedCard


def build_footer(view) -> None:
    theme = view.theme
    view.compact_footer = RoundedCard(
        view.background,
        theme=theme,
        scale=view.s,
        height=view.s(94),
        padding=10,
    )
    view.compact_footer.grid(
        row=3,
        column=0,
        columnspan=2,
        sticky="ew",
        padx=view.s(12),
        pady=(view.s(8), 0),
    )

    footer = view.compact_footer.content
    footer.grid_columnconfigure(0, weight=1, uniform="compact_launch")
    footer.grid_columnconfigure(1, weight=1, uniform="compact_launch")

    tk.Label(
        footer,
        text="CURRENT PROJECT",
        bg=theme["surface_1"],
        fg=theme["text_muted"],
        anchor="w",
        font=("Segoe UI Semibold", 8),
    ).grid(row=0, column=0, columnspan=2, sticky="ew")

    tk.Label(
        footer,
        textvariable=view.selected_var,
        bg=theme["surface_1"],
        fg=theme["text_secondary"],
        anchor="w",
        font=("Cascadia Code", 8),
    ).grid(
        row=1,
        column=0,
        columnspan=2,
        sticky="ew",
        pady=(view.s(3), view.s(6)),
    )

    view.compact_claude_button = GlassBrandButton(
        footer,
        role="claude",
        text="Claude Code",
        command=lambda: view._launch("claude"),
        theme=theme,
        scale=view.s,
        width=145,
        height=38,
    )
    view.compact_claude_button.grid(
        row=2,
        column=0,
        sticky="ew",
        padx=(0, view.s(4)),
    )

    view.compact_hermes_button = GlassBrandButton(
        footer,
        role="hermes",
        text="Hermes",
        command=lambda: view._launch("hermes"),
        theme=theme,
        scale=view.s,
        width=120,
        height=38,
    )
    view.compact_hermes_button.grid(
        row=2,
        column=1,
        sticky="ew",
        padx=(view.s(4), 0),
    )
