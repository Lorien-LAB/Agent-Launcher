from __future__ import annotations

import tkinter as tk

from launcher_settings_models import project_summary
from launcher_widgets import GhostButton, RoundedCard


class CurrentProjectCard(RoundedCard):
    def __init__(self, master, *, theme, scale, callbacks):
        self.theme = theme
        self.s = scale
        self.callbacks = callbacks
        super().__init__(
            master,
            theme=theme,
            scale=scale,
            height=scale(102),
            padding=8,
        )
        body = self.content
        body.grid_columnconfigure(1, weight=1)
        self.name_var = tk.StringVar(value="No project selected")
        self.path_var = tk.StringVar(value="Choose a project from the list")
        tk.Label(
            body,
            text="CURRENT PROJECT",
            bg=theme["surface_1"],
            fg=theme["text_muted"],
            anchor="w",
            font=("Segoe UI Semibold", 8),
        ).grid(row=0, column=0, columnspan=2, sticky="ew")
        tk.Label(
            body,
            text="◆",
            bg=theme["surface_1"],
            fg=theme["blue_light"],
            font=("Segoe UI Symbol", 10),
        ).grid(row=1, column=0, rowspan=2, sticky="n", pady=(scale(4), 0))
        tk.Label(
            body,
            textvariable=self.name_var,
            bg=theme["surface_1"],
            fg=theme["text_primary"],
            anchor="w",
            font=("Segoe UI Semibold", 9),
        ).grid(row=1, column=1, sticky="ew", padx=(scale(7), 0), pady=(scale(3), 0))
        tk.Label(
            body,
            textvariable=self.path_var,
            bg=theme["surface_1"],
            fg=theme["text_muted"],
            anchor="w",
            justify="left",
            wraplength=scale(350),
            font=("Cascadia Code", 8),
        ).grid(row=2, column=1, sticky="ew", padx=(scale(7), 0))
        actions = tk.Frame(body, bg=theme["surface_1"])
        actions.grid(
            row=3,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(scale(5), 0),
        )
        actions.grid_columnconfigure(0, weight=1, uniform="project")
        actions.grid_columnconfigure(1, weight=1, uniform="project")
        self.open_button = GhostButton(
            actions,
            text="Open Explorer",
            command=callbacks.on_open_explorer,
            theme=theme,
            scale=scale,
            width=130,
            height=28,
        )
        self.open_button.grid(row=0, column=0, sticky="ew", padx=(0, scale(4)))
        self.copy_button = GhostButton(
            actions,
            text="Copy Path",
            command=callbacks.on_copy_path,
            theme=theme,
            scale=scale,
            width=110,
            height=28,
        )
        self.copy_button.grid(row=0, column=1, sticky="ew", padx=(scale(4), 0))
        self.set_project(None)

    def set_project(self, path):
        summary = project_summary(path)
        self.name_var.set(summary.name)
        self.path_var.set(summary.path)
        self.open_button.configure_state(summary.actions_enabled)
        self.copy_button.configure_state(summary.actions_enabled)
