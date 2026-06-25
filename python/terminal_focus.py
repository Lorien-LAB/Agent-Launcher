"""Windows Terminal focus helpers for Session Monitor card clicks."""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import os


def ancestor_chain(start_pid, parent_map, max_depth=32):
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


def windows_process_parent_map():
    """Read the Windows process tree with Toolhelp32Snapshot."""
    if os.name != "nt":
        return {}

    class ProcessEntry32W(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD),
            ("th32DefaultHeapID", ctypes.c_void_p),
            ("th32ModuleID", wintypes.DWORD),
            ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD),
            ("pcPriClassBase", wintypes.LONG),
            ("dwFlags", wintypes.DWORD),
            ("szExeFile", wintypes.WCHAR * 260),
        ]

    kernel32 = ctypes.windll.kernel32
    kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    snapshot = kernel32.CreateToolhelp32Snapshot(0x00000002, 0)
    invalid_handle = ctypes.c_void_p(-1).value
    if not snapshot or snapshot == invalid_handle:
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


def find_terminal_hwnd_for_session_pid(core, session_pid):
    """Resolve a Claude PID to its owning Windows Terminal top-level window."""
    if os.name != "nt":
        return None

    ancestors = set(ancestor_chain(session_pid, windows_process_parent_map()))
    if not ancestors:
        return None

    user32 = ctypes.windll.user32
    found_hwnd = None
    enum_proc_type = ctypes.WINFUNCTYPE(
        wintypes.BOOL,
        wintypes.HWND,
        wintypes.LPARAM,
    )

    @enum_proc_type
    def enum_window(hwnd, _lparam):
        nonlocal found_hwnd
        class_buffer = ctypes.create_unicode_buffer(64)
        user32.GetClassNameW(hwnd, class_buffer, 63)
        if class_buffer.value != core.WT_CLASS:
            return True

        window_pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(window_pid))
        if int(window_pid.value) in ancestors:
            found_hwnd = hwnd
            return False
        return True

    user32.EnumWindows(enum_window, 0)
    return found_hwnd


def raise_hwnd_preserving_geometry(hwnd) -> bool:
    """Raise a window without changing its saved position or dimensions."""
    if os.name != "nt":
        return False

    try:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        if not user32.IsWindow(hwnd):
            return False

        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, 9)  # SW_RESTORE

        current_thread = kernel32.GetCurrentThreadId()
        target_thread = user32.GetWindowThreadProcessId(hwnd, None)
        foreground = user32.GetForegroundWindow()
        foreground_thread = (
            user32.GetWindowThreadProcessId(foreground, None)
            if foreground
            else 0
        )

        attached = []
        for thread_id in {target_thread, foreground_thread}:
            if (
                thread_id
                and thread_id != current_thread
                and user32.AttachThreadInput(current_thread, thread_id, True)
            ):
                attached.append(thread_id)

        try:
            flags = 0x0001 | 0x0002 | 0x0040 | 0x0200
            topmost = ctypes.c_void_p(-1)
            not_topmost = ctypes.c_void_p(-2)

            # Toggle topmost only long enough to move the window above others.
            # NOMOVE and NOSIZE preserve its existing geometry.
            first_raise = user32.SetWindowPos(
                hwnd, topmost, 0, 0, 0, 0, flags
            )
            user32.SetWindowPos(
                hwnd, not_topmost, 0, 0, 0, 0, flags
            )
            user32.BringWindowToTop(hwnd)
            activated = user32.SetForegroundWindow(hwnd)
            user32.SetActiveWindow(hwnd)
            user32.SetFocus(hwnd)
            return bool(
                first_raise
                or activated
                or user32.GetForegroundWindow() == hwnd
            )
        finally:
            for thread_id in attached:
                user32.AttachThreadInput(current_thread, thread_id, False)
    except Exception:
        return False


def find_terminal_hwnd_by_title(core, cwd):
    """Fallback lookup when process ancestry cannot resolve a window."""
    if os.name != "nt" or not cwd:
        return None

    directory_name = os.path.basename(cwd)
    if not directory_name:
        return None

    user32 = ctypes.windll.user32
    found_hwnd = None
    enum_proc_type = ctypes.WINFUNCTYPE(
        wintypes.BOOL,
        wintypes.HWND,
        wintypes.LPARAM,
    )

    @enum_proc_type
    def enum_window(hwnd, _lparam):
        nonlocal found_hwnd
        class_buffer = ctypes.create_unicode_buffer(64)
        user32.GetClassNameW(hwnd, class_buffer, 63)
        if class_buffer.value != core.WT_CLASS:
            return True

        title_buffer = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(hwnd, title_buffer, 255)
        if directory_name.casefold() in title_buffer.value.casefold():
            found_hwnd = hwnd
            return False
        return True

    user32.EnumWindows(enum_window, 0)
    return found_hwnd


def apply_terminal_focus(core) -> None:
    """Install PID-aware card click behavior onto the launcher classes."""
    def card_click(self, _event=None):
        if self.snapshot:
            self.on_activate(self.snapshot)

    def bring_terminal_by_title(self, cwd):
        hwnd = find_terminal_hwnd_by_title(core, cwd)
        if not hwnd:
            return
        normalized = os.path.normpath(cwd).lower()
        with core._HWND_LOCK:
            core._terminal_hwnds[normalized] = hwnd
        raise_hwnd_preserving_geometry(hwnd)

    def bring_terminal_to_front(self, target=None):
        if target is None:
            return

        snapshot = target if hasattr(target, "cwd") else None
        cwd = snapshot.cwd if snapshot is not None else str(target)
        session_pid = getattr(snapshot, "pid", 0) if snapshot is not None else 0

        if session_pid:
            hwnd = find_terminal_hwnd_for_session_pid(core, session_pid)
            if hwnd:
                if cwd:
                    normalized = os.path.normpath(cwd).lower()
                    with core._HWND_LOCK:
                        core._terminal_hwnds[normalized] = hwnd
                if raise_hwnd_preserving_geometry(hwnd):
                    return

        if cwd:
            normalized = os.path.normpath(cwd).lower()
            with core._HWND_LOCK:
                hwnd = core._terminal_hwnds.get(normalized)
            if hwnd and raise_hwnd_preserving_geometry(hwnd):
                return
            self._bring_terminal_by_title(cwd)

    core.SessionCard._on_click = card_click
    core.TerminalManager._bring_terminal_by_title = bring_terminal_by_title
    core.TerminalManager._bring_terminal_to_front = bring_terminal_to_front
