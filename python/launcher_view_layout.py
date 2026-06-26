from __future__ import annotations

import tkinter as tk

from launcher_view_models import layout_spec


class LauncherViewLayout:
    def _apply_layout(self, expanded):
        spec = layout_spec(expanded)
        left_weight, right_weight = spec.column_weights
        uniform = "launcher_equal_columns" if expanded else ""
        self.background.grid_columnconfigure(
            0,
            weight=left_weight if expanded else 1,
            minsize=0,
            uniform=uniform,
        )
        self.background.grid_columnconfigure(
            1,
            weight=right_weight if expanded else 0,
            minsize=0,
            uniform=uniform,
        )
        if expanded:
            self.directory_list.grid_configure(
                columnspan=1,
                padx=(self.s(12), self.s(5)),
            )
            self.settings_panel.grid(
                row=2,
                column=1,
                sticky="nsew",
                padx=(self.s(5), self.s(12)),
            )
            self.compact_footer.grid_remove()
        else:
            self.settings_panel.grid_remove()
            self.directory_list.grid_configure(
                columnspan=2,
                padx=(self.s(12), self.s(12)),
            )
            self.compact_footer.grid()
        self.background.set_expanded(expanded)
        self.titlebar.set_expanded(expanded)

    def set_expanded(self, expanded):
        self.expanded = bool(expanded)
        self._apply_layout(self.expanded)

    def prepare_mode_transition(self, expanding):
        self._transition_expanding = bool(expanding)
        if expanding:
            self.background.set_expanded(True)
            self.titlebar.set_expanded(True)
        else:
            self.expanded = False
            self._apply_layout(False)

    def update_mode_transition(self, expanding, progress):
        progress = max(0.0, min(1.0, float(progress)))
        if expanding and progress >= 0.45 and not self.expanded:
            self.expanded = True
            self._apply_layout(True)

    def finish_mode_transition(self, expanded):
        self._transition_expanding = None
        self.set_expanded(expanded)

    def reduced_motion_enabled(self):
        return bool(
            getattr(self.root, "_launcher_reduced_motion", False)
        )

    def set_launch_options(self, options):
        self.settings_panel.set_launch_options(options)

    def set_appearance(self, settings):
        self.settings_panel.set_appearance(settings)

    def set_appearance_dirty(self, dirty, applied_now=False):
        self.settings_panel.set_appearance_dirty(dirty, applied_now)

    def get_scroll_fraction(self):
        return self.directory_list.scroll_fraction()

    def restore_scroll_fraction(self, fraction):
        self.directory_list.restore_scroll(fraction)

    def destroy(self):
        if self._destroyed:
            return
        self._destroyed = True
        try:
            self.search_var.trace_remove("write", self._search_trace)
        except (tk.TclError, AttributeError):
            pass
        try:
            self.background.destroy()
        except tk.TclError:
            pass
