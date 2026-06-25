from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from launcher_state import AppearanceSettings, LaunchOptions


class LauncherSettingsPanel(tk.Frame):
    def __init__(self, master, colors, scale, callbacks):
        super().__init__(master, bg=colors["card"])
        self.colors = colors
        self.s = scale
        self.callbacks = callbacks

        self.project_name_var = tk.StringVar(value="No project selected")
        self.project_path_var = tk.StringVar(value="—")
        self.terminal_mode_var = tk.StringVar(value="window")
        self.skip_permissions_var = tk.BooleanVar(value=False)
        self.hide_after_launch_var = tk.BooleanVar(value=False)
        self.appearance_mode_var = tk.StringVar(value="none")
        self.opacity_var = tk.IntVar(value=50)
        self.opacity_text_var = tk.StringVar(value="50%")
        self._build()

    def _build(self):
        c = self.colors
        self.grid_columnconfigure(0, weight=1)
        tk.Label(self, text="Current Project", bg=c["card"], fg=c["text"], font=("Segoe UI", 11, "bold")).grid(row=0, column=0, sticky="w", padx=10, pady=(10, 2))
        tk.Label(self, textvariable=self.project_name_var, bg=c["card"], fg=c["accent"], font=("Segoe UI", 10, "bold")).grid(row=1, column=0, sticky="w", padx=10)
        tk.Label(self, textvariable=self.project_path_var, bg=c["card"], fg=c["sub"], wraplength=self.s(300), justify="left", font=("Consolas", 8)).grid(row=2, column=0, sticky="ew", padx=10, pady=(2, 6))

        project_buttons = tk.Frame(self, bg=c["card"])
        project_buttons.grid(row=3, column=0, sticky="ew", padx=10)
        tk.Button(project_buttons, text="Open Explorer", command=self.callbacks.on_open_explorer, relief="flat").pack(side="left")
        tk.Button(project_buttons, text="Copy Path", command=self.callbacks.on_copy_path, relief="flat").pack(side="left", padx=(6, 0))

        tk.Label(self, text="Launch Options", bg=c["card"], fg=c["text"], font=("Segoe UI", 10, "bold")).grid(row=4, column=0, sticky="w", padx=10, pady=(12, 2))
        launch_modes = tk.Frame(self, bg=c["card"])
        launch_modes.grid(row=5, column=0, sticky="ew", padx=10)
        for value, text in (("window", "New window"), ("tab", "New tab")):
            tk.Radiobutton(
                launch_modes,
                text=text,
                value=value,
                variable=self.terminal_mode_var,
                command=self._launch_options_changed,
                bg=c["card"], fg=c["text"], selectcolor=c["list"],
                activebackground=c["card"],
            ).pack(side="left")
        tk.Label(self, text="Tab focus is window-level only", bg=c["card"], fg=c["muted"], font=("Segoe UI", 8)).grid(row=6, column=0, sticky="w", padx=10)
        tk.Checkbutton(
            self,
            text="Skip permission confirmation",
            variable=self.skip_permissions_var,
            command=self._launch_options_changed,
            bg=c["card"], fg=c["text"], selectcolor=c["list"],
            activebackground=c["card"],
        ).grid(row=7, column=0, sticky="w", padx=10)
        tk.Checkbutton(
            self,
            text="Hide Launcher after launch",
            variable=self.hide_after_launch_var,
            command=self._launch_options_changed,
            bg=c["card"], fg=c["text"], selectcolor=c["list"],
            activebackground=c["card"],
        ).grid(row=8, column=0, sticky="w", padx=10)

        tk.Label(self, text="Terminal Appearance", bg=c["card"], fg=c["text"], font=("Segoe UI", 10, "bold")).grid(row=9, column=0, sticky="w", padx=10, pady=(12, 2))
        appearance_modes = tk.Frame(self, bg=c["card"])
        appearance_modes.grid(row=10, column=0, sticky="ew", padx=10)
        for value, text in (("acrylic", "Acrylic"), ("opacity", "Opacity"), ("none", "Solid")):
            tk.Radiobutton(
                appearance_modes,
                text=text,
                value=value,
                variable=self.appearance_mode_var,
                command=self._appearance_changed,
                bg=c["card"], fg=c["text"], selectcolor=c["list"],
                activebackground=c["card"],
            ).pack(side="left")

        opacity_row = tk.Frame(self, bg=c["card"])
        opacity_row.grid(row=11, column=0, sticky="ew", padx=10, pady=(4, 0))
        opacity_row.grid_columnconfigure(0, weight=1)
        self.opacity_scale = ttk.Scale(
            opacity_row,
            from_=0,
            to=100,
            variable=self.opacity_var,
            command=self._opacity_changed,
        )
        self.opacity_scale.grid(row=0, column=0, sticky="ew")
        tk.Label(opacity_row, textvariable=self.opacity_text_var, bg=c["card"], fg=c["text"], width=5).grid(row=0, column=1)

        actions = tk.Frame(self, bg=c["card"])
        actions.grid(row=12, column=0, sticky="ew", padx=10, pady=(8, 10))
        tk.Button(actions, text="Cancel Preview", command=self.callbacks.on_appearance_cancel, relief="flat").pack(side="left")
        tk.Button(actions, text="Apply", command=self.callbacks.on_appearance_apply, relief="flat").pack(side="right")
        self._update_opacity_state()

    def _launch_options_changed(self):
        self.callbacks.on_launch_options_changed(
            LaunchOptions(
                terminal_mode=self.terminal_mode_var.get(),
                skip_permissions=self.skip_permissions_var.get(),
                hide_after_launch=self.hide_after_launch_var.get(),
            )
        )

    def _appearance_changed(self):
        self._update_opacity_state()
        self._emit_preview()

    def _opacity_changed(self, value):
        opacity = int(float(value))
        self.opacity_text_var.set(f"{opacity}%")
        self._emit_preview()

    def _emit_preview(self):
        self.callbacks.on_appearance_preview(
            AppearanceSettings(
                mode=self.appearance_mode_var.get(),
                opacity=int(self.opacity_var.get()),
            )
        )

    def _update_opacity_state(self):
        state = "disabled" if self.appearance_mode_var.get() == "none" else "normal"
        self.opacity_scale.configure(state=state)

    def set_project(self, path):
        self.project_name_var.set(__import__("os").path.basename(path) if path else "No project selected")
        self.project_path_var.set(path or "—")

    def set_launch_options(self, options):
        self.terminal_mode_var.set(options.terminal_mode)
        self.skip_permissions_var.set(options.skip_permissions)
        self.hide_after_launch_var.set(options.hide_after_launch)

    def set_appearance(self, settings):
        self.appearance_mode_var.set(settings.mode)
        self.opacity_var.set(settings.opacity)
        self.opacity_text_var.set(f"{settings.opacity}%")
        self._update_opacity_state()
