from __future__ import annotations

from pathlib import Path

from launcher_logging import configure_launcher_logger
from launcher_runtime_dependencies import build_launcher_dependencies
from launcher_runtime_helpers import launcher_window_sizes, reduced_motion_enabled
from launcher_runtime_session import initialize_session_monitor
from launcher_state import LauncherStateStore
from launcher_theme import COLORS


APP_DIR = Path.home() / ".agent-launcher"
STATE_PATH = APP_DIR / "launcher-state.json"
LOG_PATH = APP_DIR / "agent-launcher.log"


def initialize_adaptive_manager(manager, root, core) -> None:
    manager.root = root
    manager.root.title("Agent Launcher")
    manager.scale = core.get_dpi_scale()
    manager.root.tk.call("tk", "scaling", manager.scale)
    manager.root.configure(bg=COLORS["window_bg"])
    manager.root.resizable(True, True)
    manager.root._launcher_reduced_motion = reduced_motion_enabled()

    manager.logger = configure_launcher_logger(LOG_PATH)
    manager.state_store = LauncherStateStore(
        STATE_PATH,
        logger=manager.logger,
    )
    state = manager.state_store.load()

    manager.compact_size, manager.expanded_size = launcher_window_sizes(
        manager.scale
    )
    manager.w, manager.h = manager.compact_size
    manager.root.minsize(manager.w, manager.h)
    x, y = manager._clamp_launcher_position(
        state.window_x,
        state.window_y,
        manager.w,
        manager.h,
    )
    manager.root.geometry(f"{manager.w}x{manager.h}+{x}+{y}")
    manager.root.update_idletasks()

    build_launcher_dependencies(manager, core)
    initialize_session_monitor(manager, core)
