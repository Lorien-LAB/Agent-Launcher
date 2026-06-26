from __future__ import annotations

import tkinter as tk

from launcher_quiet_branding import QuietGlassBrandButton
from launcher_state import LaunchOptions
from launcher_surfaces import CleanRoundedCard
from launcher_theme import METRICS
from launcher_widgets import SegmentedControl, ToggleSwitch


class LaunchOptionsCard(CleanRoundedCard):
    def __init__(self, master, *, theme, scale, callbacks):
        self.theme = theme
        self.s = scale
        self.callbacks = callbacks
        self.mode_var = tk.StringVar(value="window")
        self.skip_var = tk.BooleanVar(value=False)
        self.hide_var = tk.BooleanVar(value=False)
        self.panel_bg = theme["glass_content"]
        self.panel_theme = dict(theme)
        self.panel_theme["surface_1"] = self.panel_bg
        super().__init__(
            master,
            theme=theme,
            scale=scale,
            height=scale(180),
            radius=METRICS.card_radius,
            padding=8,
        )
        body = self.content
        body.grid_columnconfigure(0, weight=1)
        tk.Label(
            body,
            text="LAUNCH OPTIONS",
            bg=self.panel_bg,
            fg=theme["text_muted"],
            anchor="w",
            font=("Segoe UI Semibold", 8),
        ).grid(row=0, column=0, sticky="ew")
        self.mode_control = SegmentedControl(
            body,
            options=(("window", "New window"), ("tab", "New tab")),
            variable=self.mode_var,
            command=lambda _value: self._changed(),
            theme=self.panel_theme,
            scale=scale,
            height=30,
        )
        self.mode_control.grid(row=1, column=0, sticky="ew", pady=(scale(5), 0))
        self.tab_hint = tk.Label(
            body,
            text="Terminal window focus only; exact tab focus is not guaranteed.",
            bg=self.panel_bg,
            fg=theme["text_muted"],
            anchor="w",
            justify="left",
            wraplength=scale(350),
            font=("Segoe UI", 8),
        )
        self.tab_hint.grid(row=2, column=0, sticky="ew", pady=(scale(3), 0))

        toggles = tk.Frame(body, bg=self.panel_bg)
        toggles.grid(row=3, column=0, sticky="ew", pady=(scale(5), 0))
        toggles.grid_columnconfigure(0, weight=1)
        tk.Label(
            toggles,
            text="Skip confirmation prompts",
            bg=self.panel_bg,
            fg=theme["text_secondary"],
            anchor="w",
            font=("Segoe UI", 9),
        ).grid(row=0, column=0, sticky="ew")
        self.skip_toggle = ToggleSwitch(
            toggles,
            variable=self.skip_var,
            command=lambda _value: self._changed(),
            theme=self.panel_theme,
            scale=scale,
        )
        self.skip_toggle.grid(row=0, column=1, padx=(scale(8), 0))
        tk.Label(
            toggles,
            text="Hide Launcher after launch",
            bg=self.panel_bg,
            fg=theme["text_secondary"],
            anchor="w",
            font=("Segoe UI", 9),
        ).grid(row=1, column=0, sticky="ew", pady=(scale(4), 0))
        self.hide_toggle = ToggleSwitch(
            toggles,
            variable=self.hide_var,
            command=lambda _value: self._changed(),
            theme=self.panel_theme,
            scale=scale,
        )
        self.hide_toggle.grid(row=1, column=1, padx=(scale(8), 0), pady=(scale(4), 0))

        buttons = tk.Frame(body, bg=self.panel_bg)
        buttons.grid(row=4, column=0, sticky="ew", pady=(scale(6), 0))
        buttons.grid_columnconfigure(0, weight=1, uniform="launch")
        buttons.grid_columnconfigure(1, weight=1, uniform="launch")
        self.claude_button = QuietGlassBrandButton(
            buttons,
            role="claude",
            text="Claude Code",
            command=lambda: callbacks.on_launch("claude"),
            theme=self.panel_theme,
            scale=scale,
            width=135,
            height=34,
        )
        self.claude_button.grid(row=0, column=0, sticky="ew", padx=(0, scale(4)))
        self.hermes_button = QuietGlassBrandButton(
            buttons,
            role="hermes",
            text="Hermes",
            command=lambda: callbacks.on_launch("hermes"),
            theme=self.panel_theme,
            scale=scale,
            width=115,
            height=34,
        )
        self.hermes_button.grid(row=0, column=1, sticky="ew", padx=(scale(4), 0))
        self._update_hint()

    def _changed(self):
        self._update_hint()
        self.callbacks.on_launch_options_changed(
            LaunchOptions(
                terminal_mode=self.mode_var.get(),
                skip_permissions=self.skip_var.get(),
                hide_after_launch=self.hide_var.get(),
            )
        )

    def _update_hint(self):
        if self.mode_var.get() == "tab":
            self.tab_hint.grid()
        else:
            self.tab_hint.grid_remove()

    def set_options(self, options):
        self.mode_control.set_value(options.terminal_mode, emit=False)
        self.skip_toggle.set_value(options.skip_permissions, emit=False)
        self.hide_toggle.set_value(options.hide_after_launch, emit=False)
        self._update_hint()
