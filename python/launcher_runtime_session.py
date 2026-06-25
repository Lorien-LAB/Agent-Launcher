from __future__ import annotations


def initialize_session_monitor(manager, core) -> None:
    manager._tray = None
    manager._tray_icon = None
    manager._stats = None
    manager._stats_panel = None
    manager._animation_phase = 0.0
    manager._animation_after_id = None
    manager._panel_resize_after_id = None
    manager._last_statuses = {}
    manager._done_until = {}
    manager._session_cards = {}
    manager._expanded_session_id = None
    manager._position_after_id = None

    manager._create_stats_panel()
    manager._monitor = core.SessionMonitor()
    manager._monitor.on_update(manager._on_stats_update)
    manager._monitor.scan()
    manager._monitor.start()

    manager.root.protocol("WM_DELETE_WINDOW", manager._hide_to_tray)
    manager.root.bind(
        "<Configure>",
        manager._on_launcher_configure,
        add="+",
    )
    manager.root.bind("<Map>", manager._on_launcher_map, add="+")
    manager.root.after(100, manager._create_tray)
    manager._animation_after_id = manager.root.after(
        200,
        manager._animate_loop,
    )
