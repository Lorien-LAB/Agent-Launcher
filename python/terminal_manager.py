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
        if hasattr(self, "_hide_details"):
            self._hide_details()
        self.on_height_changed()


def _ancestor_chain(start_pid, parent_map, max_depth=32):
    """Return a PID and its ancestors, stopping at cycles or missing parents."""
    chain = []
    seen = set()
    try:
        current = int(start_pid)
    except (TypeError, ValueError):
        return chain

    for _ in range(max_depth):
        if current <= 0 or current in seen:
            break
        chain.append(current)
        seen.add(current)
        current = int(parent_map.get(current, 0) or 0)
    return chain


def _windows_process_parent_map():
    """Read the Windows process tree with Toolhelp32Snapshot."""
    if os.name != "nt":
        return {}

    class ProcessEntry32W(ctypes.Structure):
        _fields_ = [
            ("dwSize", ctypes.c_ulong),
            ("cntUsage", ctypes.c_ulong),
            ("th32ProcessID", ctypes.c_ulong),
            ("th32DefaultHeapID", ctypes.c_void_p),
            ("th32ModuleID", ctypes.c_ulong),
            ("cntThreads", ctypes.c_ulong),
            ("th32ParentProcessID", ctypes.c_ulong),
            ("pcPriClassBase", ctypes.c_long),
            ("dwFlags", ctypes.c_ulong),
            ("szExeFile", ctypes.c_wchar * 260),
        ]

    kernel32 = ctypes.windll.kernel32
    snapshot = kernel32.CreateToolhelp32Snapshot(0x00000002, 0)
    invalid_handle = ctypes.c_void_p(-1).value
    if snapshot in (0, invalid_handle):
        return {}

    parents = {}
    entry = ProcessEntry32W()
    entry.dwSize = ctypes.sizeof(entry)
    try:
        has_entry = kernel32.Process32FirstW(snapshot, ctypes.byref(entry))
        while has_entry:
            parents[int(entry.th32ProcessID)] = int(entry.th32ParentProcessID)
            has_entry = kernel32.Process32NextW(snapshot, ctypes.byref(entry))
    finally:
        kernel32.CloseHandle(snapshot)
    return parents


def _find_terminal_hwnd_for_session_pid(session_pid):
    """Resolve a Claude PID to its owning Windows Terminal top-level window."""
    if os.name != "nt":
        return None

    parent_map = _windows_process_parent_map()
    ancestors = set(_ancestor_chain(session_pid, parent_map))
    if not ancestors:
        return None

    user32 = ctypes.windll.user32
    found_hwnd = None

    @ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_long, ctypes.c_long)
    def enum_window(hwnd, _lparam):
        nonlocal found_hwnd

        class_buffer = ctypes.create_unicode_buffer(64)
        user32.GetClassNameW(hwnd, class_buffer, 63)
        if class_buffer.value != _core.WT_CLASS:
            return 1

        window_pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(window_pid))
        if int(window_pid.value) in ancestors:
            found_hwnd = hwnd
            return 0
        return 1

    user32.EnumWindows(enum_window, 0)
    return found_hwnd


def _raise_hwnd_preserving_geometry(hwnd) -> bool:
    """Bring a window forward without changing its position or dimensions."""
    try:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        if not user32.IsWindow(hwnd):
            return False

        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, 9)  # SW_RESTORE: restores saved placement.

        current_thread = kernel32.GetCurrentThreadId()
        target_thread = user32.GetWindowThreadProcessId(hwnd, None)
        foreground = user32.GetForegroundWindow()
        foreground_thread = (
            user32.GetWindowThreadProcessId(foreground, None)
            if foreground
            else 0
        )

        attached_threads = []
        for thread_id in {target_thread, foreground_thread}:
            if (
                thread_id
                and thread_id != current_thread
                and user32.AttachThreadInput(current_thread, thread_id, True)
            ):
                attached_threads.append(thread_id)

        try:
            # Temporarily toggle TOPMOST to guarantee a Z-order raise, then
            # immediately remove TOPMOST. NOMOVE/NOSIZE preserve geometry.
            swp_nosize = 0x0001
            swp_nomove = 0x0002
            swp_showwindow = 0x0040
            swp_noownerzorder = 0x0200
            flags = swp_nosize | swp_nomove | swp_showwindow | swp_noownerzorder

            user32.AllowSetForegroundWindow(-1)
            user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, flags)  # HWND_TOPMOST
            user32.SetWindowPos(hwnd, -2, 0, 0, 0, 0, flags)  # HWND_NOTOPMOST
            user32.BringWindowToTop(hwnd)
            user32.SetForegroundWindow(hwnd)
            user32.SetActiveWindow(hwnd)
            user32.SetFocus(hwnd)
            return user32.GetForegroundWindow() == hwnd
        finally:
            for thread_id in attached_threads:
                user32.AttachThreadInput(current_thread, thread_id, False)
    except Exception:
        return False


def _bring_terminal_by_title_preserving_geometry(self, cwd):
    """Fallback: find a matching Windows Terminal title and raise it."""
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
            if directory_name.casefold() in title_buffer.value.casefold():
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


def _bring_terminal_to_front_preserving_geometry(self, target=None):
    """Raise the clicked session terminal, preserving its placement and size."""
    if target is None:
        return

    snapshot = target if hasattr(target, "cwd") else None
    cwd = snapshot.cwd if snapshot is not None else str(target)
    session_pid = getattr(snapshot, "pid", 0) if snapshot is not None else 0

    if session_pid:
        hwnd = _find_terminal_hwnd_for_session_pid(session_pid)
        if hwnd:
            if cwd:
                normalized = os.path.normpath(cwd).lower()
                with _core._HWND_LOCK:
                    _core._terminal_hwnds[normalized] = hwnd
            if _raise_hwnd_preserving_geometry(hwnd):
                return

    if cwd:
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
_ancestor_pids = _ancestor_chain
_raise_terminal_window = _raise_hwnd_preserving_geometry


if __name__ == "__main__":
    _core.main()
