from __future__ import annotations

from launcher_runtime_helpers import current_monitor_work_area


class LauncherWindowMixin:
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
        core = self._runtime_core
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

    def _on_launcher_map(self, event):
        if event.widget is self.root:
            self._schedule_chrome_reapply()

    def _schedule_chrome_reapply(self):
        if self._chrome_reapply_pending:
            return
        self._chrome_reapply_pending = True
        core = self._runtime_core

        def apply():
            self._chrome_reapply_pending = False
            self.chrome_controller.apply_frameless()

        try:
            self.root.after_idle(apply)
        except core.tk.TclError:
            self._chrome_reapply_pending = False

    def _minimize_launcher(self):
        if self.chrome_controller.minimize_native():
            return
        self._hide_to_tray()

    def _toggle_launcher_maximize(self):
        state = self.chrome_controller.state
        if state.maximized and state.restore_bounds is not None:
            bounds = state.restore_bounds
            self.root.geometry(
                f"{bounds.width}x{bounds.height}+{bounds.x}+{bounds.y}"
            )
            state.mark_restored()
            self.launcher_view.titlebar.set_maximized(False)
            return

        restore_bounds = self.chrome_controller.current_bounds()
        work = current_monitor_work_area(self.root)
        state.mark_maximized(restore_bounds)
        self.root.geometry(
            f"{work.width}x{work.height}+{work.x}+{work.y}"
        )
        self.launcher_view.titlebar.set_maximized(True)

    def _hide_to_tray(self):
        self.launcher_coordinator.hide_to_tray()

    def _restore_window(self):
        core = self._runtime_core
        try:
            self.root.deiconify()
            self.root.update_idletasks()
            self.chrome_controller.apply_frameless()
            self.root.lift()
            self.root.focus_force()
        except core.tk.TclError:
            pass
