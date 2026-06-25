"""Python Agent Launcher entry point.

The stable launcher implementation lives in ``terminal_manager_core`` while
presentation overrides keep the Session Monitor compact and easy to iterate.
"""
import ctypes
import os
import time

import session_panel_layout as _panel_layout
import session_panel_ui as _panel_ui
import terminal_manager_core as _core


_panel_ui.apply_session_panel_overrides(_core)
_panel_layout.apply_compact_layout(_core)


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
            # Avoid resetting the sawtooth progress phase on every height frame.
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
        self.on_height_changed()


def _raise_hwnd_preserving_geometry(hwnd) -> bool:
    """Bring a window to the front without changing its position or size."""
    try:
        user32 = ctypes.windll.user32
        if not user32.IsWindow(hwnd):
            return False

        # Restore a minimized terminal to its previous normal placement.
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, 9)  # SW_RESTORE

        hwnd_top = 0
        swp_nosize = 0x0001
        swp_nomove = 0x0002
        swp_showwindow = 0x0040
        swp_noownerzorder = 0x0200
        flags = swp_nosize | swp_nomove | swp_showwindow | swp_noownerzorder

        user32.SetWindowPos(hwnd, hwnd_top, 0, 0, 0, 0, flags)
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
        return True
    except Exception:
        return False


def _bring_terminal_by_title_preserving_geometry(self, cwd):
    """Find the matching Windows Terminal and raise it without repositioning."""
    try:
        user32 = ctypes.windll.user32
        directory_name = os.path.basename(cwd) if cwd else ""
        if not directory_name:
            return

        found_hwnd = None

        @ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_long, ctypes.c_long)
        def enum_window(hwnd, _lparam):
            nonlocal found_hwnd

            class_buffer = ctypes.create_unicode_buffer(64)
            user32.GetClassNameW(hwnd, class_buffer, 63)
            if class_buffer.value != _core.WT_CLASS:
                return 1

            title_buffer = ctypes.create_unicode_buffer(256)
            user32.GetWindowTextW(hwnd, title_buffer, 255)
            if directory_name in title_buffer.value:
                found_hwnd = hwnd
                return 0
            return 1

        user32.EnumWindows(enum_window, 0)

        if found_hwnd:
            normalized = os.path.normpath(cwd).lower()
            with _core._HWND_LOCK:
                _core._terminal_hwnds[normalized] = found_hwnd
            _raise_hwnd_preserving_geometry(found_hwnd)
    except Exception:
        pass


def _bring_terminal_to_front_preserving_geometry(self, cwd=None):
    """Activate the clicked session terminal without moving or resizing it."""
    if not cwd:
        return

    normalized = os.path.normpath(cwd).lower()
    with _core._HWND_LOCK:
        hwnd = _core._terminal_hwnds.get(normalized)

    if hwnd and _raise_hwnd_preserving_geometry(hwnd):
        return

    self._bring_terminal_by_title(cwd)


_core.SessionCard._tick_height = _smooth_tick_height
_core.TerminalManager._bring_terminal_by_title = (
    _bring_terminal_by_title_preserving_geometry
)
_core.TerminalManager._bring_terminal_to_front = (
    _bring_terminal_to_front_preserving_geometry
)

# Re-export the core module's public and testable helpers so existing imports
# of ``terminal_manager`` continue to work.
for _name in dir(_core):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_core, _name)

_animated_progress_width = _panel_ui._animated_progress_width
_session_is_open = _panel_ui._session_is_open
_filter_live_stats = _panel_ui._filter_live_stats
_compact_branch = _panel_layout._compact_branch
_raise_terminal_window = _raise_hwnd_preserving_geometry


if __name__ == "__main__":
    _core.main()
