from __future__ import annotations

import tkinter as tk

from launcher_settings_models import appearance_status_text
from launcher_state import AppearanceSettings
from launcher_surfaces import CleanRoundedCard
from launcher_widgets import GhostButton, PrimaryButton, SegmentedControl, ThemedSlider


class TerminalAppearanceCard(CleanRoundedCard):
    def __init__(self, master, *, theme, scale, callbacks):
        self.theme = theme
        self.s = scale
        self.callbacks = callbacks
        self.mode_var = tk.StringVar(value="none")
        self.opacity_var = tk.IntVar(value=50)
        self.opacity_text_var = tk.StringVar(value="50%")
        self.status_var = tk.StringVar(value="No changes")
        self.dirty = False
        super().__init__(
            master,
            theme=theme,
            scale=scale,
            height=scale(144),
            radius=18,
            padding=8,
        )
        body = self.content
        body.grid_columnconfigure(0, weight=1)
        tk.Label(body, text="TERMINAL APPEARANCE", bg=theme["surface_1"], fg=theme["text_muted"], anchor="w", font=("Segoe UI Semibold", 8)).grid(row=0, column=0, sticky="ew")
        self.mode_control = SegmentedControl(
            body,
            options=(("acrylic", "Acrylic"), ("opacity", "Opacity"), ("none", "Solid")),
            variable=self.mode_var,
            command=lambda _value: self._changed(),
            theme=theme,
            scale=scale,
            height=30,
        )
        self.mode_control.grid(row=1, column=0, sticky="ew", pady=(scale(4), 0))

        opacity_row = tk.Frame(body, bg=theme["surface_1"])
        opacity_row.grid(row=2, column=0, sticky="ew", pady=(scale(4), 0))
        opacity_row.grid_columnconfigure(0, weight=1)
        self.slider = ThemedSlider(opacity_row, variable=self.opacity_var, command=self._opacity_changed, theme=theme, scale=scale, from_=0, to=100)
        self.slider.grid(row=0, column=0, sticky="ew")
        tk.Label(opacity_row, textvariable=self.opacity_text_var, bg=theme["surface_1"], fg=theme["text_secondary"], width=5, font=("Cascadia Code", 8)).grid(row=0, column=1, padx=(scale(6), 0))

        actions = tk.Frame(body, bg=theme["surface_1"])
        actions.grid(row=3, column=0, sticky="ew", pady=(scale(5), 0))
        actions.grid_columnconfigure(0, weight=1)
        self.status_label = tk.Label(actions, textvariable=self.status_var, bg=theme["surface_1"], fg=theme["text_muted"], anchor="w", font=("Segoe UI", 8))
        self.status_label.grid(row=0, column=0, sticky="ew")
        self.cancel_button = GhostButton(actions, text="Cancel", command=callbacks.on_appearance_cancel, theme=theme, scale=scale, width=72, height=28)
        self.cancel_button.grid(row=0, column=1, padx=(scale(6), 0))
        self.apply_button = PrimaryButton(actions, role="accent", text="Apply", command=callbacks.on_appearance_apply, theme=theme, scale=scale, width=68, height=28)
        self.apply_button.grid(row=0, column=2, padx=(scale(6), 0))
        self.set_dirty(False)
        self._update_slider()

    def _changed(self):
        self._update_slider()
        self._emit_preview()

    def _opacity_changed(self, value):
        opacity = int(round(float(value)))
        self.opacity_var.set(opacity)
        self.opacity_text_var.set(f"{opacity}%")
        self._emit_preview()

    def _emit_preview(self):
        self.callbacks.on_appearance_preview(
            AppearanceSettings(mode=self.mode_var.get(), opacity=int(self.opacity_var.get()))
        )

    def _update_slider(self):
        self.slider.set_enabled(self.mode_var.get() != "none")

    def set_settings(self, settings):
        self.mode_control.set_value(settings.mode, emit=False)
        self.opacity_var.set(settings.opacity)
        self.opacity_text_var.set(f"{settings.opacity}%")
        self._update_slider()
        self.set_dirty(False)

    def set_dirty(self, dirty: bool, applied_now: bool = False):
        self.dirty = bool(dirty)
        self.status_var.set(appearance_status_text(self.dirty, bool(applied_now)))
        color = self.theme["warning"] if self.dirty else self.theme["success"] if applied_now else self.theme["text_muted"]
        self.status_label.configure(fg=color)
        self.apply_button.configure_state(self.dirty)
        self.cancel_button.configure_state(self.dirty)
