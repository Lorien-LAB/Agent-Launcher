from __future__ import annotations

import os

from launcher_view import COMPACT_SIZE, EXPANDED_SIZE, LauncherCallbacks
from launcher_state import normalize_path


class LauncherCoordinator:
    def __init__(
        self,
        root,
        state_store,
        directory_index,
        window_animator,
        appearance_controller,
        launch_controller,
        logger=None,
    ):
        self.root = root
        self.state_store = state_store
        self.directory_index = directory_index
        self.window_animator = window_animator
        self.appearance_controller = appearance_controller
        self.launch_controller = launch_controller
        self.logger = logger
        self.view = None
        self.selected_directory = None
        self.expanded = False

    def callbacks(self):
        return LauncherCallbacks(
            on_select=self.select_directory,
            on_launch=self.launch_selected,
            on_toggle_favorite=self.toggle_favorite,
            on_search=self.search,
            on_refresh_index=self.refresh_index,
            on_toggle_expanded=self.toggle_mode,
            on_launch_options_changed=self.state_store.update_launch_options,
            on_appearance_preview=self.preview_appearance,
            on_appearance_apply=self.apply_appearance,
            on_appearance_cancel=self.cancel_appearance,
            on_open_explorer=self.open_selected_directory,
            on_copy_path=self.copy_selected_path,
            on_remove_recent=self.remove_recent,
        )

    def attach_view(self, view):
        self.view = view
        state = self.state_store.state
        self.view.set_launch_options(state.launch_options)
        self.view.set_appearance(self.appearance_controller.applied_settings)
        self.view.render_home(state.favorites, state.recent_directories)
        if self.state_store.recovered_corrupt_file:
            self.view.set_status("Launcher configuration was reset", error=True)
        self.refresh_index()

    def refresh_index(self):
        if not self.view:
            return
        self.view.set_indexing(True)
        self.view.set_status("Building directory index…")
        started = self.directory_index.refresh_async(
            scheduler=lambda callback: self.root.after(0, callback),
            on_complete=self._index_complete,
        )
        if not started:
            self.view.set_status("Directory index is already refreshing")

    def _index_complete(self, snapshot, failures):
        if not self.view:
            return
        self.view.set_indexing(False)
        if failures:
            self.view.set_status(
                f"Indexed {len(snapshot)} directories; some paths failed",
                error=True,
            )
        else:
            self.view.set_status(f"Indexed {len(snapshot)} directories")
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

    def select_directory(self, path):
        self.selected_directory = path
        if self.view:
            self.view.set_selected_path(path)

    def toggle_favorite(self, path):
        try:
            self.state_store.toggle_favorite(path)
        except (FileNotFoundError, OSError) as exc:
            self._set_error(f"Unable to update favorite: {exc}")
            return
        self._render_current_query()

    def remove_recent(self, path):
        try:
            changed = self.state_store.remove_recent(path)
        except OSError as exc:
            self._set_error(f"Unable to remove recent directory: {exc}")
            return
        if changed:
            self._render_current_query()

    def search(self, query):
        if not self.view:
            return
        if not query.strip():
            self.view.render_home(
                self.state_store.state.favorites,
                self.state_store.state.recent_directories,
            )
            return
        recent_count = len(self.state_store.state.recent_directories)
        recent_rank = {
            path: float(recent_count - index)
            for index, path in enumerate(self.state_store.state.recent_directories)
        }
        results = self.directory_index.search(query, recent_rank)
        favorites = {
            normalize_path(path) for path in self.state_store.state.favorites
        }
        self.view.render_search_results(
            [entry.path for entry in results],
            favorites,
        )

    def _render_current_query(self):
        if not self.view:
            return
        self.search(self.view.search_var.get())

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
        self.view.set_status(f"Launched {project}")
        if self.state_store.state.launch_options.hide_after_launch:
            self.hide_to_tray()

    def toggle_mode(self):
        if not self.view or self.window_animator.running:
            return
        expanding = not self.expanded
        if not expanding and self.appearance_controller.is_dirty:
            restored = self.appearance_controller.cancel()
            self.view.set_appearance(restored)
        self.expanded = expanding
        self.view.set_expanded(expanding)
        target = EXPANDED_SIZE if expanding else COMPACT_SIZE
        available_width = max(1, self.root.winfo_screenwidth() - self.root.winfo_x())
        available_height = max(1, self.root.winfo_screenheight() - self.root.winfo_y())
        self.window_animator.animate_to(
            target[0],
            target[1],
            available_width,
            available_height,
        )

    def preview_appearance(self, settings):
        try:
            self.appearance_controller.preview(settings)
        except OSError as exc:
            self._set_error(f"Appearance preview failed: {exc}")

    def apply_appearance(self):
        try:
            self.appearance_controller.apply()
        except OSError as exc:
            self._set_error(f"Appearance apply failed: {exc}")
            return
        self.view.set_status("Terminal appearance applied")

    def cancel_appearance(self):
        try:
            restored = self.appearance_controller.cancel()
        except OSError as exc:
            self._set_error(f"Appearance rollback failed: {exc}")
            return
        self.view.set_appearance(restored)
        self.view.set_status("Terminal appearance preview cancelled")

    def open_selected_directory(self):
        if not self.selected_directory or not os.path.isdir(self.selected_directory):
            self._set_error("Selected directory is unavailable")
            return
        try:
            os.startfile(self.selected_directory)
        except (AttributeError, OSError) as exc:
            self._set_error(f"Unable to open directory: {exc}")

    def copy_selected_path(self):
        if not self.selected_directory:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(self.selected_directory)
        self.view.set_status("Path copied")

    def persist_position(self):
        try:
            self.state_store.update_window_position(
                self.root.winfo_x(),
                self.root.winfo_y(),
            )
            self.state_store.save()
        except OSError as exc:
            if self.logger:
                self.logger.warning("failed to persist launcher position: %s", exc)

    def hide_to_tray(self):
        if self.appearance_controller.is_dirty:
            try:
                restored = self.appearance_controller.cancel()
                if self.view:
                    self.view.set_appearance(restored)
            except OSError as exc:
                self._set_error(f"Appearance rollback failed: {exc}")
                return
        self.persist_position()
        self.root.withdraw()

    def shutdown(self):
        self.window_animator.cancel()
        self.directory_index.stop()
        try:
            self.appearance_controller.cancel()
        except OSError as exc:
            if self.logger:
                self.logger.warning("appearance rollback during shutdown failed: %s", exc)
        self.persist_position()
        if self.view:
            self.view.destroy()
            self.view = None

    def _set_error(self, message):
        if self.view:
            self.view.set_status(message, error=True)
        if self.logger:
            self.logger.warning("launcher operation failed: %s", message)
