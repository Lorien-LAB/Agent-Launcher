from __future__ import annotations

import tkinter as tk

from launcher_appearance_card import TerminalAppearanceCard
from launcher_launch_card import LaunchOptionsCard
from launcher_project_card import CurrentProjectCard
from launcher_settings_models import appearance_status_text, project_summary, resolved_theme


class LauncherSettingsPanel(tk.Frame):
    def __init__(
        self,
        master,
        colors=None,
        scale=lambda value: value,
        callbacks=None,
        *,
        theme=None,
    ):
        self.theme = resolved_theme(theme, colors)
        self.s = scale
        self.callbacks = callbacks
        super().__init__(master, bg=self.theme["window_bg"])
        self.grid_columnconfigure(0, weight=1)

        self.current_project_card = CurrentProjectCard(
            self,
            theme=self.theme,
            scale=self.s,
            callbacks=callbacks,
        )
        self.current_project_card.grid(row=0, column=0, sticky="ew")

        self.launch_options_card = LaunchOptionsCard(
            self,
            theme=self.theme,
            scale=self.s,
            callbacks=callbacks,
        )
        self.launch_options_card.grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(self.s(10), 0),
        )

        self.appearance_card = TerminalAppearanceCard(
            self,
            theme=self.theme,
            scale=self.s,
            callbacks=callbacks,
        )
        self.appearance_card.grid(
            row=2,
            column=0,
            sticky="ew",
            pady=(self.s(10), 0),
        )

    def set_project(self, path):
        self.current_project_card.set_project(path)

    def set_launch_options(self, options):
        self.launch_options_card.set_options(options)

    def set_appearance(self, settings):
        self.appearance_card.set_settings(settings)

    def set_appearance_dirty(self, dirty: bool, applied_now: bool = False):
        self.appearance_card.set_dirty(dirty, applied_now)


__all__ = [
    "LauncherSettingsPanel",
    "appearance_status_text",
    "project_summary",
]
