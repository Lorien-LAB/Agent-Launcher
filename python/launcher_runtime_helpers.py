from __future__ import annotations

import ctypes
from ctypes import wintypes
import sys

from launcher_chrome import WindowBounds
from launcher_theme import compact_size, expanded_size


MONITOR_DEFAULTTONEAREST = 2
SPI_GETCLIENTAREAANIMATION = 0x1042


class _MonitorInfo(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", wintypes.RECT),
        ("rcWork", wintypes.RECT),
        ("dwFlags", wintypes.DWORD),
    ]


def launcher_window_sizes(dpi_scale: float):
    return compact_size(dpi_scale), expanded_size(dpi_scale)


def current_monitor_work_area(root) -> WindowBounds:
    fallback = WindowBounds(
        0,
        0,
        max(1, int(root.winfo_screenwidth())),
        max(1, int(root.winfo_screenheight())),
    )
    if sys.platform != "win32":
        return fallback
    try:
        user32 = ctypes.windll.user32
        hwnd = int(root.winfo_id())
        monitor = user32.MonitorFromWindow(
            ctypes.c_void_p(hwnd),
            MONITOR_DEFAULTTONEAREST,
        )
        info = _MonitorInfo()
        info.cbSize = ctypes.sizeof(_MonitorInfo)
        if not user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
            return fallback
        rect = info.rcWork
        return WindowBounds(
            int(rect.left),
            int(rect.top),
            max(1, int(rect.right - rect.left)),
            max(1, int(rect.bottom - rect.top)),
        )
    except (AttributeError, OSError, TypeError, ValueError):
        return fallback


def reduced_motion_enabled() -> bool:
    if sys.platform != "win32":
        return False
    enabled = wintypes.BOOL()
    try:
        ok = ctypes.windll.user32.SystemParametersInfoW(
            SPI_GETCLIENTAREAANIMATION,
            0,
            ctypes.byref(enabled),
            0,
        )
    except (AttributeError, OSError):
        return False
    return bool(ok) and not bool(enabled.value)
