from __future__ import annotations

from directory_index import DirectoryIndex
from launch_controller import LaunchController
from launcher_animation import WindowAnimator
from launcher_chrome import LauncherChromeController
from launcher_state import AppearanceSettings
from launcher_theme import COLORS
from launcher_view import LauncherView
from launcher_visual_coordinator import VisualLauncherCoordinator
from terminal_appearance import TerminalAppearanceController
from terminal_launch_modes import launch_with_mode


def build_launcher_dependencies(manager, core) -> None:
    manager.chrome_controller = LauncherChromeController(manager.root)
    manager._chrome_reapply_pending = False

    manager.directory_index = DirectoryIndex(
        core.BASE_DIRS,
        logger=manager.logger,
    )
    manager.window_animator = WindowAnimator(manager.root, scale=manager.s)
    manager.appearance_controller = TerminalAppearanceController(
        reader=lambda: AppearanceSettings(*core.get_current_mode()),
        writer=lambda settings: core.apply_background(
            settings.mode,
            settings.opacity,
        ),
        persist=manager.state_store.update_appearance,
        logger=manager.logger,
    )
    manager.launch_controller = LaunchController(
        launcher=lambda **kwargs: launch_with_mode(
            core.launch_in_terminal,
            **kwargs,
        ),
        state_store=manager.state_store,
        claude_path=core.CLAUDE_PATH,
        hermes_path=core.HERMES_PATH,
        claude_skip_args=core.CLAUDE_ARGS,
        logger=manager.logger,
    )
    manager.launcher_coordinator = VisualLauncherCoordinator(
        root=manager.root,
        state_store=manager.state_store,
        directory_index=manager.directory_index,
        window_animator=manager.window_animator,
        appearance_controller=manager.appearance_controller,
        launch_controller=manager.launch_controller,
        logger=manager.logger,
    )
    manager.launcher_view = LauncherView(
        manager.root,
        callbacks=manager.launcher_coordinator.callbacks(),
        theme=COLORS,
        scale=manager.s,
        chrome_controller=manager.chrome_controller,
        on_minimize=manager._minimize_launcher,
        on_toggle_maximize=manager._toggle_launcher_maximize,
        on_close=manager._hide_to_tray,
    )
    manager.launcher_view.set_expanded(False)
    manager.launcher_coordinator.attach_view(manager.launcher_view)
    manager.root.update_idletasks()
    manager.chrome_controller.apply_frameless()
