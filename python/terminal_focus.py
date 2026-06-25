"""Stable one-to-one routing between Claude sessions and Terminal windows."""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import json
import os
import subprocess
import threading
import time
import uuid

from session_monitor import SESSIONS_DIR


REGISTRY_PATH = os.path.join(
    os.path.expanduser("~"), ".agent-launcher", "session-windows.json"
)
MATCH_WINDOW_SECONDS = 180.0


def _normalize_cwd(path: str) -> str:
    return os.path.normpath(path or "").replace("\\", "/").casefold()


def choose_pending_launch(cwd: str, created_at: float, pending: list[dict]):
    """Match a new session to the nearest pending launch in the same cwd."""
    target = _normalize_cwd(cwd)
    candidates = []
    for entry in pending:
        if _normalize_cwd(entry.get("cwd", "")) != target:
            continue
        launched_at = float(entry.get("launched_at", 0.0) or 0.0)
        delta = float(created_at or 0.0) - launched_at
        if -5.0 <= delta <= MATCH_WINDOW_SECONDS:
            candidates.append((abs(delta), entry))
    if not candidates:
        return None
    return min(candidates, key=lambda item: item[0])[1]


def _session_created_at(snapshot) -> float:
    """Use the session metadata file creation time for launch correlation."""
    try:
        path = os.path.join(SESSIONS_DIR, f"{int(snapshot.pid)}.json")
        return os.path.getctime(path)
    except (OSError, TypeError, ValueError):
        return float(getattr(snapshot, "updated_at", 0.0) or 0.0)


class SessionWindowRegistry:
    """Persist launch-token to Claude-session mappings across app restarts."""

    def __init__(self, path=REGISTRY_PATH):
        self.path = path
        self._lock = threading.RLock()
        self._data = {"version": 1, "pending": [], "sessions": {}}
        self._load()

    def _load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as handle:
                loaded = json.load(handle)
            if isinstance(loaded, dict):
                self._data["pending"] = list(loaded.get("pending", []))
                self._data["sessions"] = dict(loaded.get("sessions", {}))
        except (OSError, json.JSONDecodeError, TypeError):
            pass

    def _save(self):
        directory = os.path.dirname(self.path)
        os.makedirs(directory, exist_ok=True)
        temporary = self.path + ".tmp"
        with open(temporary, "w", encoding="utf-8") as handle:
            json.dump(self._data, handle, ensure_ascii=False, indent=2)
        os.replace(temporary, self.path)

    def register_launch(self, cwd, window_name, title_token, launched_at=None):
        entry = {
            "launch_id": window_name,
            "window_name": window_name,
            "title_token": title_token,
            "cwd": cwd,
            "launched_at": float(launched_at or time.time()),
        }
        with self._lock:
            self._data["pending"].append(entry)
            self._save()
        return entry

    def remove_pending(self, window_name):
        with self._lock:
            self._data["pending"] = [
                entry for entry in self._data["pending"]
                if entry.get("window_name") != window_name
            ]
            self._save()

    def reconcile(self, sessions):
        now = time.time()
        with self._lock:
            pending = [
                entry for entry in self._data["pending"]
                if now - float(entry.get("launched_at", 0.0) or 0.0) < 600
            ]
            mappings = self._data["sessions"]
            changed = pending != self._data["pending"]

            for snapshot in sessions:
                sid = str(getattr(snapshot, "session_id", "") or "")
                if not sid or sid in mappings:
                    continue
                match = choose_pending_launch(
                    getattr(snapshot, "cwd", ""),
                    _session_created_at(snapshot),
                    pending,
                )
                if not match:
                    continue
                mappings[sid] = {
                    "window_name": match["window_name"],
                    "title_token": match["title_token"],
                    "cwd": getattr(snapshot, "cwd", ""),
                    "mapped_at": now,
                }
                pending = [
                    entry for entry in pending
                    if entry.get("window_name") != match.get("window_name")
                ]
                changed = True

            self._data["pending"] = pending
            if changed:
                self._save()

    def lookup(self, session_id):
        with self._lock:
            mapping = self._data["sessions"].get(str(session_id), None)
            return dict(mapping) if mapping else None


_REGISTRY = SessionWindowRegistry()


def _enum_terminal_windows(core):
    """Return ``[(hwnd, title)]`` for all Windows Terminal top-level windows."""
    if os.name != "nt":
        return []

    user32 = ctypes.windll.user32
    enum_proc_type = ctypes.WINFUNCTYPE(
        wintypes.BOOL, wintypes.HWND, wintypes.LPARAM
    )
    user32.EnumWindows.argtypes = [enum_proc_type, wintypes.LPARAM]
    user32.EnumWindows.restype = wintypes.BOOL
    user32.GetClassNameW.argtypes = [
        wintypes.HWND, wintypes.LPWSTR, ctypes.c_int
    ]
    user32.GetWindowTextW.argtypes = [
        wintypes.HWND, wintypes.LPWSTR, ctypes.c_int
    ]

    windows = []

    @enum_proc_type
    def callback(hwnd, _lparam):
        class_buffer = ctypes.create_unicode_buffer(64)
        user32.GetClassNameW(hwnd, class_buffer, 63)
        if class_buffer.value == core.WT_CLASS:
            title_buffer = ctypes.create_unicode_buffer(512)
            user32.GetWindowTextW(hwnd, title_buffer, 511)
            windows.append((hwnd, title_buffer.value))
        return True

    user32.EnumWindows(callback, 0)
    return windows


def find_terminal_hwnd_by_token(core, title_token):
    matches = [
        hwnd for hwnd, title in _enum_terminal_windows(core)
        if title_token and title_token.casefold() in title.casefold()
    ]
    return matches[0] if len(matches) == 1 else None


def find_unique_terminal_hwnd_by_cwd(core, cwd):
    """Legacy fallback; refuse to guess when duplicate titles exist."""
    directory_name = os.path.basename(cwd or "").casefold()
    if not directory_name:
        return None
    matches = [
        hwnd for hwnd, title in _enum_terminal_windows(core)
        if directory_name in title.casefold()
    ]
    return matches[0] if len(matches) == 1 else None


def raise_hwnd_preserving_geometry(hwnd) -> bool:
    """Raise a window without changing its saved position or dimensions."""
    if os.name != "nt":
        return False
    try:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        user32.IsWindow.argtypes = [wintypes.HWND]
        user32.IsWindow.restype = wintypes.BOOL
        user32.IsIconic.argtypes = [wintypes.HWND]
        user32.IsIconic.restype = wintypes.BOOL
        user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
        user32.GetForegroundWindow.restype = wintypes.HWND
        user32.GetWindowThreadProcessId.argtypes = [
            wintypes.HWND, ctypes.POINTER(wintypes.DWORD)
        ]
        user32.GetWindowThreadProcessId.restype = wintypes.DWORD
        user32.AttachThreadInput.argtypes = [
            wintypes.DWORD, wintypes.DWORD, wintypes.BOOL
        ]
        user32.SetWindowPos.argtypes = [
            wintypes.HWND, wintypes.HWND,
            ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
            wintypes.UINT,
        ]
        user32.SetWindowPos.restype = wintypes.BOOL
        user32.SetForegroundWindow.argtypes = [wintypes.HWND]
        user32.SetForegroundWindow.restype = wintypes.BOOL
        kernel32.GetCurrentThreadId.restype = wintypes.DWORD

        if not user32.IsWindow(hwnd):
            return False
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, 9)

        current_thread = kernel32.GetCurrentThreadId()
        target_thread = user32.GetWindowThreadProcessId(hwnd, None)
        foreground = user32.GetForegroundWindow()
        foreground_thread = (
            user32.GetWindowThreadProcessId(foreground, None)
            if foreground else 0
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
            raised = user32.SetWindowPos(
                hwnd, wintypes.HWND(-1), 0, 0, 0, 0, flags
            )
            user32.SetWindowPos(
                hwnd, wintypes.HWND(-2), 0, 0, 0, 0, flags
            )
            user32.BringWindowToTop(hwnd)
            activated = user32.SetForegroundWindow(hwnd)
            return bool(raised or activated or user32.GetForegroundWindow() == hwnd)
        finally:
            for thread_id in attached:
                user32.AttachThreadInput(current_thread, thread_id, False)
    except Exception:
        return False


def _focus_named_window(window_name):
    """Ask Windows Terminal to focus its uniquely named window."""
    try:
        subprocess.Popen(
            ["wt", "-w", window_name, "focus-tab", "-t", "0"],
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return True
    except OSError:
        return False


def apply_terminal_focus(core) -> None:
    """Install unique launch naming, persistent mapping, and card activation."""
    original_on_stats_update = core.TerminalManager._on_stats_update

    def launch_in_terminal(dir_path, exe_path, args, title):
        if not os.path.isdir(dir_path):
            return False

        token = uuid.uuid4().hex[:12]
        window_name = f"agent-{token}"
        title_token = f"AL-{token}"
        dir_tag = os.path.basename(dir_path)
        stable_title = f"{title} — {dir_tag} · {title_token}"
        safe_title = stable_title.replace("'", "''")
        safe_exe = exe_path.replace("'", "''")
        script = (
            f"$Host.UI.RawUI.WindowTitle = '{safe_title}'{os.linesep}"
            f"& '{safe_exe}' {args}{os.linesep}"
        )
        temporary = os.path.join(
            os.environ.get("TEMP", os.path.expanduser("~")),
            f"launch_{token}.ps1",
        )

        try:
            with open(temporary, "w", encoding="utf-8") as handle:
                handle.write(script)
            _REGISTRY.register_launch(
                dir_path, window_name, title_token, time.time()
            )
            subprocess.Popen(
                [
                    "wt", "-w", window_name,
                    "new-tab", "-d", dir_path,
                    "--title", stable_title,
                    "--suppressApplicationTitle",
                    "pwsh", "-NoExit", "-File", temporary,
                ],
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except (OSError, ValueError):
            _REGISTRY.remove_pending(window_name)
            try:
                os.remove(temporary)
            except OSError:
                pass
            return False

        def cleanup():
            time.sleep(5)
            try:
                os.remove(temporary)
            except OSError:
                pass

        threading.Thread(target=cleanup, daemon=True, name="tmp-cleanup").start()
        return True

    def launch_claude(dir_path):
        return launch_in_terminal(
            dir_path, core.CLAUDE_PATH, core.CLAUDE_ARGS, "Claude Code"
        )

    def launch_hermes(dir_path):
        return launch_in_terminal(
            dir_path, core.HERMES_PATH, "", "Hermes"
        )

    def on_stats_update(self, stats):
        _REGISTRY.reconcile(stats.sessions)
        original_on_stats_update(self, stats)

    def card_click(self, _event=None):
        if self.snapshot:
            self.on_activate(self.snapshot)

    def bring_terminal_to_front(self, target=None):
        if target is None:
            return
        snapshot = target if hasattr(target, "session_id") else None
        cwd = getattr(snapshot, "cwd", "") if snapshot else str(target)

        if snapshot:
            mapping = _REGISTRY.lookup(snapshot.session_id)
            if mapping:
                hwnd = find_terminal_hwnd_by_token(
                    core, mapping.get("title_token", "")
                )
                if hwnd and raise_hwnd_preserving_geometry(hwnd):
                    return
                if _focus_named_window(mapping.get("window_name", "")):
                    return

        # Only use the old title fallback when it is unambiguous. Never choose
        # one of several same-directory windows, which caused wrong-session focus.
        hwnd = find_unique_terminal_hwnd_by_cwd(core, cwd)
        if hwnd:
            raise_hwnd_preserving_geometry(hwnd)

    core.launch_in_terminal = launch_in_terminal
    core.launch_claude = launch_claude
    core.launch_hermes = launch_hermes
    core.TerminalManager._on_stats_update = on_stats_update
    core.SessionCard._on_click = card_click
    core.TerminalManager._bring_terminal_to_front = bring_terminal_to_front
