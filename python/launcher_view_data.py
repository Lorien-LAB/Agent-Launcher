from __future__ import annotations

from launcher_state import normalize_path
from launcher_view_models import DirectoryRow, compose_home_rows, truncate_middle


_STATUS_COLORS = {
    "normal": "text_muted",
    "success": "success",
    "warning": "warning",
    "error": "danger",
}


class LauncherViewData:
    def _search_changed(self, *_args):
        if not self._destroyed:
            self.callbacks.on_search(self.search_var.get())

    def _launch(self, agent_type):
        self.callbacks.on_launch(agent_type)
        return "break"

    def _move_selection(self, delta):
        path = self.directory_list.move_selection(delta)
        if path:
            self.callbacks.on_select(path)
        return "break"

    def render_home(self, favorites, recents):
        self.directory_list.render(compose_home_rows(favorites, recents))

    def render_search_results(self, paths, favorites):
        rows = [
            DirectoryRow("search", path, normalize_path(path) in favorites)
            for path in paths
        ]
        self.directory_list.render(rows)

    def set_selected_path(self, path):
        self.selected_path = path
        self.selected_var.set(
            truncate_middle(path or "No directory selected", 56)
        )
        self.directory_list.set_selected(path)
        self.settings_panel.set_project(path)

    def set_status(self, message, level="normal", error=None):
        if error is not None:
            level = "error" if error else "normal"
        if level not in _STATUS_COLORS:
            level = "normal"
        color = self.theme[_STATUS_COLORS[level]]
        self.status_var.set(message)
        self.status_label.configure(fg=color)
        self.status_dot.configure(fg=color)

    def set_indexing(self, active):
        self.refresh_button.configure_state(not bool(active))
