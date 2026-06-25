from __future__ import annotations

import tkinter as tk

from launcher_state import LaunchOptions
from launcher_widgets import PrimaryButton, RoundedCard, SegmentedControl, ToggleSwitch


class LaunchOptionsCard(RoundedCard):
    def __init__(self, master, *, theme, scale, callbacks):
        self.theme = theme
        self.s = scale
        self.callbacks = callbacks
        self.mode_var = tk.StringVar(value="window")
        self.skip_var = tk.BooleanVar(value=False)
        self.hide_var = tk.BooleanVar(value=False)
        super().__init__(master, theme=theme, scale=scale, height=scale(182))
        body = self.content
        body.grid_columnconfigure(0, weight=1)
        tk.Label(body, text="LAUNCH OPTIONS", bg=theme["surface_1"], fg=theme["text_muted"], anchor="w", font=("Segoe UI Semibold", 8)).grid(row=0, column=0, sticky="ew")
        self.mode_control = SegmentedControl(body, options=(("window", "New window"), ("tab", "New tab")), variable=self.mode_var, command=lambda _value: self._changed(), theme=theme, scale=scale)
        self.mode_control.grid(row=1, column=0, sticky="ew", pady=(scale(6), 0))
        self.tab_hint = tk.Label(body, text="Terminal window focus only; exact tab focus is not guaranteed.", bg=theme["surface_1"], fg=theme["text_muted"], anchor="w", justify="left", wraplength=scale(350), font=("Segoe UI", 8))
        self.tab_hint.grid(row=2, column=0, sticky="ew", pady=(scale(3), 0))
        toggles = tk.Frame(body, bg=theme["surface_1"])
        toggles.grid(row=3, column=0, sticky="ew", pady=(scale(5), 0))
        toggles.grid_columnconfigure(0, weight=1)
        tk.Label(toggles, text="Skip confirmation prompts", bg=theme["surface_1"], fg=theme["text_secondary"], anchor="w", font=("Segoe UI", 9)).grid(row=0, column=0, sticky="ew")
        self.skip_toggle = ToggleSwitch(toggles, variable=self.skip_var, command=lambda _value: self._changed(), theme=theme, scale=scale)
        self.skip_toggle.grid(row=0, column=1, padx=(scale(8), 0))
        tk.Label(toggles, text="Hide Launcher after launch", bg=theme["surface_1"], fg=theme["text_secondary"], anchor="w", font=("Segoe UI", 9)).grid(row=1, column=0, sticky="ew", pady=(scale(5), 0))
        self.hide_toggle = ToggleSwitch(toggles, variable=self.hide_var, command=lambda _value: self._changed(), theme=theme, scale=scale)
        self.hide_toggle.grid(row=1, column=1, padx=(scale(8), 0), pady=(scale(5), 0))
        buttons = tk.Frame(body, bg=theme["surface_1"])
        buttons.grid(row=4, column=0, sticky="ew", pady=(scale(8), 0))
        buttons.grid_columnconfigure(0, weight=1, uniform="launch")
        buttons.grid_columnconfigure(1, weight=1, uniform="launch")
        claude = PrimaryButton(buttons, role="claude", text="Claude Code", command=lambda: callbacks.on_launch("claude"), theme=theme, scale=scale, width=135, height=34)
        claude.grid(row=0, column=0, sticky="ew", padx=(0, scale(4)))
        hermes = PrimaryButton(buttons, role="hermes", text="Hermes", command=lambda: callbacks.on_launch("hermes"), theme=theme, scale=scale, width=115, height=34)
        hermes.grid(row=0, column=1, sticky="ew", padx=(scale(4), 0))
        self._update_hint()

    def _changed(self):
        self._update_hint()
        self.callbacks.on_launch_options_changed(LaunchOptions(terminal_mode=self.mode_var.get(), skip_permissions=self.skip_var.get(), hide_after_launch=self.hide_var.get()))

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
