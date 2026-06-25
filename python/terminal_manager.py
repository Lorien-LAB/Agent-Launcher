"""Python Agent Launcher entry point.

The stable launcher implementation lives in ``terminal_manager_core`` while
small override modules contain the Session Monitor presentation and terminal
focus behavior.
"""
import time

import session_panel_chrome as _panel_chrome
import session_panel_layout as _panel_layout
import session_panel_ui as _panel_ui
import terminal_focus as _terminal_focus
import terminal_manager_core as _core


_panel_ui.apply_session_panel_overrides(_core)
_panel_layout.apply_compact_layout(_core)
_terminal_focus.apply_terminal_focus(_core)
_panel_chrome.apply_panel_chrome(_core)


def _smooth_tick_height(self):
    """Animate only card geometry; the panel window is resized separately."""
    self._height_after_id = None
    if self._destroyed:
        return

    elapsed = time.perf_counter() - self._animation_started_at
    t = max(0.0, min(1.0, elapsed / _panel_ui.ANIMATION_DURATION))
    eased = 1.0 - (1.0 - t) ** 3
    next_height = round(
        self._animation_from_h
        + (self._target_h - self._animation_from_h) * eased
    )

    if next_height != self._current_h:
        self._current_h = next_height
        try:
            self.frame.configure(height=self._current_h)
            self._draw_card(0.0)
        except _core.tk.TclError:
            return

    if t < 1.0:
        self._height_after_id = self.frame.after(
            _panel_ui.ANIMATION_FRAME_MS,
            self._tick_height,
        )
        return

    self._current_h = self._target_h
    try:
        self.frame.configure(height=self._current_h)
        self._draw_card(0.0)
    except _core.tk.TclError:
        return

    if not self.hovered:
        if hasattr(self, "_hide_details"):
            self._hide_details()
        self.on_height_changed()


_core.SessionCard._tick_height = _smooth_tick_height

for _name in dir(_core):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_core, _name)

_animated_progress_width = _panel_ui._animated_progress_width
_session_is_open = _panel_ui._session_is_open
_filter_live_stats = _panel_ui._filter_live_stats
_compact_branch = _panel_layout._compact_branch
_choose_pending_launch = _terminal_focus.choose_pending_launch
_raise_terminal_window = _terminal_focus.raise_hwnd_preserving_geometry


if __name__ == "__main__":
    _core.main()
