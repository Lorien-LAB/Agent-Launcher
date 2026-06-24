"""Python Agent Launcher entry point.

The stable launcher implementation lives in ``terminal_manager_core`` while
``session_panel_ui`` applies the compact Session Monitor presentation.
"""
import time

import session_panel_ui as _panel_ui
import terminal_manager_core as _core


_panel_ui.apply_session_panel_overrides(_core)


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
            # Redrawing the progress bar here would reset its sawtooth phase on
            # every 16 ms height frame and can produce visible trails.
            self._draw_card(0.0)
        except _core.tk.TclError:
            return

    if t < 1.0:
        self._height_after_id = self.frame.after(
            _panel_ui.ANIMATION_FRAME_MS, self._tick_height
        )
        return

    self._current_h = self._target_h
    try:
        self.frame.configure(height=self._current_h)
        self._draw_card(0.0)
    except _core.tk.TclError:
        return
    if not self.hovered:
        self.on_height_changed()


_core.SessionCard._tick_height = _smooth_tick_height

# Re-export the core module's public and testable helpers so existing imports
# of ``terminal_manager`` continue to work.
for _name in dir(_core):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_core, _name)

_animated_progress_width = _panel_ui._animated_progress_width
_session_is_open = _panel_ui._session_is_open
_filter_live_stats = _panel_ui._filter_live_stats


if __name__ == "__main__":
    _core.main()
