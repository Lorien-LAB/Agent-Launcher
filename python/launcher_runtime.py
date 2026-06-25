from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import threading

from directory_index import DirectoryIndex
from launch_controller import LaunchController
from launcher_animation import WindowAnimator
from launcher_coordinator import LauncherCoordinator
from launcher_logging import configure_launcher_logger
from launcher_state import AppearanceSettings, LauncherStateStore
from launcher_view import COMPACT_SIZE, LauncherView
from terminal_appearance import TerminalAppearanceController
from terminal_launch_modes import launch_with_mode


APP_DIR = Path.home() / ".agent-launcher"
STATE_PATH = APP_DIR / "launcher-state.json"
LOG_PATH = APP_DIR / "agent-launcher.log"


def install_adaptive_launcher(core):
    """Replace the legacy Launcher class while retaining patched panel methods."""
    base = core.TerminalManager

    class AdaptiveTerminalManager(base):
        def __init__(self, root):
            self.root = root
            self.root.title("Agent Launcher")
            self.scale = core.get_dpi_scale()
            self.root.tk.call("tk", "scaling", self.scale)
            self.root.configure(bg=core.C.base)
            self.root.resizable(True, True)

            self.logger = configure_launcher_logger(LOG_PATH)
            self.state_store = LauncherStateStore(STATE_PATH, logger=self.logger)
            state = self.state_store.load()

            self.w = self.s(COMPACT_SIZE[0])
            self.h = self.s(COMPACT_SIZE[1])
            self.root.minsize(self.w, self.h)
            x, y = self._clamp_launcher_position(
                state.window_x,
                state.window_y,
                self.w,
                self.h,
            )
            self.root.geometry(f"{self.w}x{self.h}+{x}+{y}")
            self.root.update_idletasks()

            self.directory_index = DirectoryIndex(core.BASE_DIRS, logger=self.logger)
            self.window_animator = WindowAnimator(self.root, scale=self.s)
            self.appearance_controller = TerminalAppearanceController(
                reader=lambda: AppearanceSettings(*core.get_current_mode()),
                writer=lambda settings: core.apply_background(
                    settings.mode,
                    settings.opacity,
                ),
                persist=self.state_store.update_appearance,
                logger=self.logger,
            )
            self.launch_controller = LaunchController(
                launcher=lambda **kwargs: launch_with_mode(
                    core.launch_in_terminal,
                    **kwargs,
                ),
                state_store=self.state_store,
                claude_path=core.CLAUDE_PATH,
                hermes_path=core.HERMES_PATH,
                claude_skip_args=core.CLAUDE_ARGS,
                logger=self.logger,
            )
            self.launcher_coordinator = LauncherCoordinator(
                root=self.root,
                state_store=self.state_store,
                directory_index=self.directory_index,
                window_animator=self.window_animator,
                appearance_controller=self.appearance_controller,
                launch_controller=self.launch_controller,
                logger=self.logger,
            )
            self.launcher_view = LauncherView(
                self.root,
                callbacks=self.launcher_coordinator.callbacks(),
                colors=self._launcher_colors(),
                scale=self.s,
            )
            self.launcher_view.set_expanded(False)
            self.launcher_coordinator.attach_view(self.launcher_view)

            self._tray = None
            self._tray_icon = None
            self._stats = None
            self._stats_panel = None
            self._animation_phase = 0.0
            self._animation_after_id = None
            self._panel_resize_after_id = None
            self._last_statuses = {}
            self._done_until = {}
            self._session_cards = {}
            self._expanded_session_id = None
            self._position_after_id = None

            self._create_stats_panel()
            self._monitor = core.SessionMonitor()
            self._monitor.on_update(self._on_stats_update)
            self._monitor.scan()
            self._monitor.start()

            self.root.protocol("WM_DELETE_WINDOW", self._hide_to_tray)
            self.root.bind("<Configure>", self._on_launcher_configure, add="+")
            self.root.after(100, self._create_tray)
            self._animation_after_id = self.root.after(200, self._animate_loop)

        def _launcher_colors(self):
            return {
                "base": core.C.base,
                "card": core.C.card,
                "list": core.C.listbg,
                "border": core.C.border,
                "selected": "#303A5C",
                "text": core.C.text,
                "sub": core.C.sub,
                "muted": core.C.subtle,
                "accent": core.C.mauve,
                "green": core.C.green,
                "orange": "#FFB86C",
                "error": core.C.red,
            }

        def _clamp_launcher_position(self, x, y, width, height):
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            return (
                max(0, min(int(x), max(0, screen_width - width))),
                max(0, min(int(y), max(0, screen_height - height))),
            )

        def _on_launcher_configure(self, event):
            if event.widget is not self.root or self.window_animator.running:
                return
            if self._position_after_id is not None:
                try:
                    self.root.after_cancel(self._position_after_id)
                except core.tk.TclError:
                    pass
            self._position_after_id = self.root.after(
                400,
                self._persist_launcher_position,
            )

        def _persist_launcher_position(self):
            self._position_after_id = None
            self.launcher_coordinator.persist_position()

        def _hide_to_tray(self):
            self.launcher_coordinator.hide_to_tray()

        def _restart_app(self):
            if threading.current_thread() is not threading.main_thread():
                try:
                    self.root.after(0, self._restart_app)
                except core.tk.TclError:
                    pass
                return
            script = os.path.join(os.path.dirname(core.__file__), "terminal_manager.py")
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
