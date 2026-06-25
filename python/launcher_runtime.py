from __future__ import annotations

import os
import subprocess
import sys
import threading

from launcher_runtime_helpers import launcher_window_sizes
from launcher_runtime_setup import (
    APP_DIR,
    LOG_PATH,
    STATE_PATH,
    initialize_adaptive_manager,
)
from launcher_runtime_window import LauncherWindowMixin


def install_adaptive_launcher(core):
    """Replace the legacy Launcher while retaining patched Session Monitor methods."""
    base = core.TerminalManager

    class AdaptiveTerminalManager(LauncherWindowMixin, base):
        _runtime_core = core
        _runtime_base = base

        def __init__(self, root):
            initialize_adaptive_manager(self, root, core)

        def _restart_app(self):
            if threading.current_thread() is not threading.main_thread():
                try:
                    self.root.after(0, self._restart_app)
                except core.tk.TclError:
                    pass
                return
            script = os.path.join(
                os.path.dirname(core.__file__),
                "terminal_manager.py",
            )
            try:
                subprocess.Popen(
                    [sys.executable, script],
                    creationflags=(
                        getattr(subprocess, "CREATE_NO_WINDOW", 0)
                        | getattr(subprocess, "DETACHED_PROCESS", 0)
                    ),
                    close_fds=True,
                )
            except OSError as exc:
                self.logger.warning("launcher restart failed: %s", exc)
                return
            self._quit_app()

        def _quit_app(self):
            if threading.current_thread() is not threading.main_thread():
                try:
                    self.root.after(0, self._quit_app)
                except core.tk.TclError:
                    pass
                return
            if self._position_after_id is not None:
                try:
                    self.root.after_cancel(self._position_after_id)
                except core.tk.TclError:
                    pass
                self._position_after_id = None
            self.launcher_coordinator.shutdown()
            base._quit_app(self)

    AdaptiveTerminalManager.__name__ = "TerminalManager"
    core.TerminalManager = AdaptiveTerminalManager
    return AdaptiveTerminalManager


__all__ = [
    "APP_DIR",
    "LOG_PATH",
    "STATE_PATH",
    "install_adaptive_launcher",
    "launcher_window_sizes",
]
