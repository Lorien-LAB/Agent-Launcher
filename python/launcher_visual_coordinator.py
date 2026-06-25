from __future__ import annotations

import os

from launcher_coordinator import LauncherCoordinator
from launcher_view import COMPACT_SIZE, EXPANDED_SIZE


class VisualLauncherCoordinator(LauncherCoordinator):
    """Visual-state aware coordinator preserving existing launch/index semantics."""

    def attach_view(self, view):
        self.view = view
        state = self.state_store.state
        self.view.set_launch_options(state.launch_options)
        self.view.set_appearance(self.appearance_controller.applied_settings)
        self.view.set_appearance_dirty(False, False)
        self.view.render_home(state.favorites, state.recent_directories)
        if self.state_store.recovered_corrupt_file:
            self.view.set_status(
                "Launcher configuration was reset",
                level="warning",
            )
        self.refresh_index()

    def _index_complete(self, snapshot, failures):
        if not self.view:
            return
        self.view.set_indexing(False)
        if failures:
            self.view.set_status(
                f"Indexed {len(snapshot)} directories; some paths failed",
                level="warning",
            )
        else:
            self.view.set_status(
                f"Indexed {len(snapshot)} directories",
                level="success",
            )
        if self.selected_directory is None:
            candidates = [
                *self.state_store.state.favorites,
                *self.state_store.state.recent_directories,
                *(entry.path for entry in snapshot),
            ]
            for path in candidates:
                if os.path.isdir(path):
                    self.select_directory(path)
                    break

    def launch_selected(self, agent_type):
        if not self.selected_directory:
            self._set_error("Select a directory first")
            return
        label = "Claude" if agent_type == "claude" else "Hermes"
        self.view.set_status(f"Launching {label}…")
        result = self.launch_controller.launch(
            agent_type,
            self.selected_directory,
            self.state_store.state.launch_options,
        )
        if not result.success:
            self._set_error(f"Launch failed: {result.error}")
            return
        self._render_current_query()
        project = os.path.basename(self.selected_directory) or self.selected_directory
        self.view.set_status(f"Launched {project}", level="success")
        if self.state_store.state.launch_options.hide_after_launch:
            self.hide_to_tray()

    def toggle_mode(self):
        if not self.view or self.window_animator.running:
            return
        expanding = not self.expanded
        if not expanding and self.appearance_controller.is_dirty:
            try:
                restored = self.appearance_controller.cancel()
            except OSError as exc:
                self._set_error(f"Appearance rollback failed: {exc}")
                return
            self.view.set_appearance(restored)
            self.view.set_appearance_dirty(False, False)

        self.expanded = expanding
        self.view.prepare_mode_transition(expanding)
        target = EXPANDED_SIZE if expanding else COMPACT_SIZE
        available_width = max(
            1,
            self.root.winfo_screenwidth() - self.root.winfo_x(),
        )
        available_height = max(
            1,
            self.root.winfo_screenheight() - self.root.winfo_y(),
        )
        started = self.window_animator.animate_to(
            target[0],
            target[1],
            available_width,
            available_height,
            on_progress=lambda progress: self.view.update_mode_transition(
                expanding,
                progress,
            ),
            on_complete=lambda: self.view.finish_mode_transition(expanding),
            reduced_motion=self.view.reduced_motion_enabled(),
        )
        if not started:
            self.view.finish_mode_transition(self.expanded)

    def preview_appearance(self, settings):
        try:
            self.appearance_controller.preview(settings)
        except OSError as exc:
            self._set_error(f"Appearance preview failed: {exc}")
            return
        if self.view:
            self.view.set_appearance_dirty(True, False)
            self.view.set_status(
                "Previewing Terminal appearance",
                level="warning",
            )

    def apply_appearance(self):
        try:
            self.appearance_controller.apply()
        except OSError as exc:
            self._set_error(f"Appearance apply failed: {exc}")
            return
        if self.view:
            self.view.set_appearance_dirty(False, True)
            self.view.set_status(
                "Terminal appearance applied",
                level="success",
            )

    def cancel_appearance(self):
        try:
            restored = self.appearance_controller.cancel()
        except OSError as exc:
            self._set_error(f"Appearance rollback failed: {exc}")
            return
        if self.view:
            self.view.set_appearance(restored)
            self.view.set_appearance_dirty(False, False)
            self.view.set_status("Terminal appearance preview cancelled")

    def copy_selected_path(self):
        if not self.selected_directory:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(self.selected_directory)
        if self.view:
            self.view.set_status("Path copied", level="success")

    def hide_to_tray(self):
        if self.appearance_controller.is_dirty:
            try:
                restored = self.appearance_controller.cancel()
                if self.view:
                    self.view.set_appearance(restored)
                    self.view.set_appearance_dirty(False, False)
            except OSError as exc:
                self._set_error(f"Appearance rollback failed: {exc}")
                return
        self.persist_position()
        self.root.withdraw()

    def _set_error(self, message):
        if self.view:
            self.view.set_status(message, level="error")
        if self.logger:
            self.logger.warning("launcher operation failed: %s", message)
